#!/usr/bin/env python3
"""Custom REPL for persona CLI with streaming and command support."""

import asyncio
import signal
from pathlib import Path
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.status import Status

from pydantic_ai import Agent
from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    ModelMessage,
    ModelResponse,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
)
from pydantic_ai.usage import RunUsage

from persona.session import SessionManager
from persona.commands import CommandRegistry


class InterruptedException(Exception):
    """Raised when user presses Ctrl+C during agent execution."""
    pass


class PersonaREPL:
    """Custom REPL loop with /commands, streaming, and rich UI."""
    
    _interrupted: bool = False
    
    def __init__(
        self,
        agent: Agent,
        session_manager: SessionManager,
        prog_name: str = "persona",
        mnt_dir: Optional[str] = None
    ):
        """Initialize the REPL.
        
        Args:
            agent: The pydantic-ai agent to use
            session_manager: SessionManager for persistence
            prog_name: Program name for display
            mnt_dir: Mount directory to display in prompt
        """
        self.agent = agent
        self.session_manager = session_manager
        self.prog_name = prog_name
        self.mnt_dir = mnt_dir
        self.console = Console()
        
        self.message_history: list[ModelMessage] = []
        
        self.current_session = "latest"
        
        self.session_usage = RunUsage()
        
        self.commands = CommandRegistry(session_manager, self.console, self)
        
        self._setup_prompt_session()
    
    def _handle_sigint(self, signum, frame):
        """Handle SIGINT by setting interrupt flag."""
        PersonaREPL._interrupted = True
    
    def _clear_interrupt(self):
        """Clear the interrupt flag."""
        PersonaREPL._interrupted = False
    
    def _check_interrupt(self):
        """Check and raise InterruptedException if flag is set."""
        if PersonaREPL._interrupted:
            PersonaREPL._interrupted = False
            raise InterruptedException()
    
    def _setup_prompt_session(self, session_name: Optional[str] = None) -> None:
        """Setup prompt_toolkit session with session-specific file history."""
        if session_name is None:
            session_name = self.current_session
        
        history_file = self.session_manager.get_command_history_path(session_name)
        history_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.prompt_session = PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
        )
    
    def switch_command_history(self, session_name: str):
        """Switch to session-specific command history."""
        self.prompt_session.history = FileHistory(
            str(self.session_manager.get_command_history_path(session_name))
        )
    
    def _get_last_request_usage(self, messages: list[ModelMessage]) -> RunUsage:
        """Get usage from the last ModelResponse only."""
        for msg in reversed(messages):
            if isinstance(msg, ModelResponse) and msg.usage:
                input_tokens = msg.usage.input_tokens
                output_tokens = msg.usage.output_tokens
                if input_tokens == 0 and msg.usage.details:
                    input_tokens = msg.usage.details.get('input_tokens', 0)
                    output_tokens = msg.usage.details.get('output_tokens', 0)
                return RunUsage(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
        return RunUsage()
    
    def reset_session(self):
        """Reset session state including usage counter."""
        self.message_history = []
        self.session_usage = RunUsage()
        self.current_session = "latest"
    
    def _display_header(self) -> None:
        """Display initial header."""
        self.console.print(f"\n[bold cyan]{self.prog_name}[/bold cyan] [dim]CLI - Type /help for commands, /exit to quit[/dim]\n")
    
    async def run(self) -> None:
        """Main REPL loop."""
        self._display_header()
        
        original_handler = signal.signal(signal.SIGINT, self._handle_sigint)
        
        try:
            while True:
                try:
                    self._clear_interrupt()
                    user_input = await self._get_input()
                    
                    if not user_input.strip():
                        continue
                    
                    if self.commands.is_command(user_input):
                        should_continue = self.commands.execute(user_input)
                        if not should_continue:
                            break
                        continue
                    
                    await self._process_with_agent(user_input)
                    
                except KeyboardInterrupt:
                    self.console.print("\n[dim]Interrupted. Type /exit to quit.[/dim]\n")
                    continue
                except InterruptedException:
                    self.console.print("\n[dim]Interrupted.[/dim]\n")
                    continue
                except EOFError:
                    self.console.print("\n[dim]Goodbye![/dim]")
                    break
                except Exception as e:
                    self.console.print(f"\n[red]Error: {str(e)}[/red]\n", markup=False)
                    import traceback
                    traceback.print_exc()
                    continue
        finally:
            signal.signal(signal.SIGINT, original_handler)
    
    async def _get_input(self) -> str:
        """Get input from user with prompt showing current session and token count."""
        loop = asyncio.get_event_loop()
        
        def get_prompt():
            tokens_str = f" [{self.session_usage.total_tokens:,} tokens]"
            mnt_str = f" [{self.mnt_dir}]" if self.mnt_dir else ""
            return self.prompt_session.prompt(f"{self.prog_name} [{self.current_session}]{tokens_str}{mnt_str} ➤ ")
        
        return await loop.run_in_executor(None, get_prompt)
    
    async def _process_with_agent(self, user_input: str) -> None:
        """Process user input with the agent using agent.iter() for full control."""
        try:
            await self._run_agent_iter(user_input)
            
            await self._auto_save()
            
        except (KeyboardInterrupt, InterruptedException):
            return
        except Exception as e:
            self.console.print(f"\n[red]Error: {e}[/red]\n")
    
    async def _run_agent_iter(self, user_input: str) -> None:
        """Run agent with agent.iter() for proper streaming and tool handling."""
        status = self.console.status("[bold cyan]Thinking...")
        status.start()
        status_active = True
        
        buffer = ""
        live = None
        interrupted = False
        
        try:
            async with self.agent.iter(
                user_input,
                message_history=self.message_history
            ) as agent_run:
                async for node in agent_run:
                    self._check_interrupt()
                    
                    if Agent.is_model_request_node(node):
                        async with node.stream(agent_run.ctx) as stream:
                            async for event in stream:
                                self._check_interrupt()
                                if isinstance(event, PartStartEvent):
                                    if isinstance(event.part, TextPart):
                                        chunk = event.part.content
                                        if chunk:
                                            if status_active:
                                                status.stop()
                                                status_active = False
                                            buffer += chunk
                                            if live is None:
                                                live = Live(
                                                    Markdown(buffer),
                                                    console=self.console,
                                                    refresh_per_second=20,
                                                )
                                                live.start()
                                            else:
                                                live.update(Markdown(buffer))
                                elif isinstance(event, PartDeltaEvent):
                                    if isinstance(event.delta, TextPartDelta):
                                        chunk = event.delta.content_delta
                                        if chunk:
                                            buffer += chunk
                                            if live is not None:
                                                live.update(Markdown(buffer))
                    
                    elif Agent.is_call_tools_node(node):
                        if live is not None:
                            live.stop()
                            live = None
                            buffer = ""
                        async with node.stream(agent_run.ctx) as handle_stream:
                            async for event in handle_stream:
                                self._check_interrupt()
                                if isinstance(event, FunctionToolCallEvent):
                                    tool_name = event.part.tool_name
                                    args = event.part.args or {}
                                    if isinstance(args, str):
                                        import json
                                        try:
                                            args = json.loads(args)
                                        except json.JSONDecodeError:
                                            args = {}
                                    if tool_name == "run_cmd":
                                        self.console.print(f"[bold orange1][CMD][/bold orange1] {args.get('cmd', '')}")
                                    elif tool_name == "save_text_file":
                                        self.console.print(f"[bold blue][FILE][/bold blue] {args.get('path', '')}")
                                    elif tool_name == "load_skill":
                                        self.console.print(f"[bold yellow][SKILL][/bold yellow] {args.get('skill', '')}")
                                    else:
                                        self.console.print(f"[dim][TOOL][/dim] {tool_name}")
                    
                    elif Agent.is_end_node(node):
                        break
                
                if live is not None:
                    live.stop()
                self.console.print()
                
                if agent_run.result is not None:
                    self.message_history = agent_run.result.all_messages()
                    self.session_usage = self._get_last_request_usage(self.message_history)
        except InterruptedException:
            interrupted = True
        except KeyboardInterrupt:
            interrupted = True
        finally:
            if status_active:
                status.stop()
            if live is not None and live.is_started:
                live.stop()
            if interrupted:
                self.console.print("\n[dim]Interrupted.[/dim]\n")
    
    async def _auto_save(self) -> None:
        """Auto-save current session to 'latest'."""
        if not self.message_history:
            return
        
        try:
            self.session_manager.save_session(
                self.message_history,
                name="latest"
            )
        except Exception:
            # Silent fail for auto-save
            pass
