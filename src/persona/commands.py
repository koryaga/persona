#!/usr/bin/env python3
"""Command registry for persona CLI /commands."""

from typing import Optional


class CommandRegistry:
    """Registry for slash commands in the persona CLI."""
    
    COMMANDS = {
        '/save': 'Save current session to disk',
        '/load': 'Load a saved session',
        '/list': 'List all saved sessions',
        '/new': 'Start a new session (clear history)',
        '/clear': 'Clear the terminal screen',
        '/help': 'Show available commands',
        '/exit': 'Exit the CLI',
    }
    
    def __init__(self, session_manager, console, repl_instance):
        """Initialize command registry.
        
        Args:
            session_manager: SessionManager instance for persistence
            console: Rich console for output
            repl_instance: PersonaREPL instance for access to message_history
        """
        self.session_manager = session_manager
        self.console = console
        self.repl = repl_instance
    
    def parse_command(self, user_input: str) -> tuple[Optional[str], list[str]]:
        """Parse user input for commands.
        
        Args:
            user_input: Raw user input
            
        Returns:
            Tuple of (command_name, args) or (None, []) if not a command
        """
        stripped = user_input.strip()
        if not stripped.startswith('/'):
            return None, []
        
        parts = stripped.split()
        command = parts[0].lower()
        args = parts[1:]
        return command, args
    
    def is_command(self, user_input: str) -> bool:
        """Check if input is a command."""
        command, _ = self.parse_command(user_input)
        return command is not None
    
    def execute(self, user_input: str) -> bool:
        """Execute a command.
        
        Args:
            user_input: The full command string
            
        Returns:
            True to continue REPL loop, False to exit
        """
        command, args = self.parse_command(user_input)
        
        if command is None:
            return True
        
        if command == '/save':
            return self._cmd_save(args)
        elif command == '/load':
            return self._cmd_load(args)
        elif command == '/list':
            return self._cmd_list()
        elif command == '/new':
            return self._cmd_new()
        elif command == '/clear':
            return self._cmd_clear()
        elif command == '/help':
            return self._cmd_help()
        elif command in ('/exit', '/quit'):
            return self._cmd_exit()
        else:
            self.console.print(f"[red]Unknown command: {command}[/red]")
            self.console.print("Type /help for available commands.")
            return True
    
    def _cmd_save(self, args: list[str]) -> bool:
        """Save current session."""
        # Generate timestamp name if no args provided, otherwise use provided name
        name = args[0] if args else None
        
        if not self.repl.message_history:
            self.console.print("[yellow]No conversation to save.[/yellow]")
            return True
        
        try:
            session_name = self.session_manager.save_session(
                self.repl.message_history,
                name=name
            )
            # Update current session name
            self.repl.current_session = session_name
            self.console.print(f"[green]Session saved: {session_name}[/green]")
        except Exception as e:
            self.console.print(f"[red]Failed to save session: {e}[/red]")
        
        return True
    
    def _cmd_load(self, args: list[str]) -> bool:
        """Load a saved session."""
        if not args:
            self.console.print("[red]Usage: /load <session_name>[/red]")
            return True
        
        name = args[0]
        messages = self.session_manager.load_session(name)
        
        if messages is None:
            self.console.print(f"[red]Session not found: {name}[/red]")
            self.console.print("Use /list to see available sessions.")
            return True
        
        self.repl.message_history = messages
        self.repl.current_session = name
        self.repl.switch_command_history(name)
        self.repl.session_usage = self.repl._get_last_request_usage(messages)
        self.console.print(f"[green]Loaded session: {name}[/green]")
        self.console.print(f"[dim]Restored {len(messages)} messages[/dim]")
        return True
    
    def _cmd_list(self) -> bool:
        """List all saved sessions."""
        sessions = self.session_manager.list_sessions()
        
        if not sessions:
            self.console.print("[dim]No saved sessions found.[/dim]")
            return True
        
        self.console.print("[bold]Saved sessions:[/bold]")
        for i, name in enumerate(sessions, 1):
            marker = " → " if name == "latest" else "   "
            self.console.print(f"{marker}{i}. {name}")
        return True
    
    def _cmd_new(self) -> bool:
        """Start a new session (clear history)."""
        self.repl.reset_session()
        self.repl.switch_command_history("latest")
        self.console.print("[green]Started new session.[/green]")
        return True
    
    def _cmd_clear(self) -> bool:
        """Clear the terminal screen."""
        import os
        os.system('clear' if os.name == 'posix' else 'cls')
        return True
    
    def _cmd_help(self) -> bool:
        """Show help message."""
        self.console.print("\n[bold cyan]Persona CLI Commands:[/bold cyan]\n")
        
        for cmd, desc in self.COMMANDS.items():
            if cmd == '/quit':
                continue  # Skip alias in help
            self.console.print(f"  [bold]{cmd:<10}[/bold]  {desc}")
        
        self.console.print("\n[dim]Commands starting with '/' are processed by the CLI.")
        self.console.print("[dim]All other input is sent to the AI agent.[/dim]\n")
        return True
    
    def _cmd_exit(self) -> bool:
        """Exit the CLI."""
        self.console.print("[dim]Goodbye![/dim]")
        return False
