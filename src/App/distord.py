import asyncio
import os
import discord
import json
from pathlib import Path
from textual.screen import ModalScreen
from textual.widgets import Button
from rich.text import Text
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog, Label
from textual.containers import Horizontal, Vertical
from textual.binding import Binding

base_dir = os.environ.get('APPDATA') or os.path.expanduser('~/.config')
CONFIG_DIR = os.path.join(base_dir, "Distord")
os.makedirs(CONFIG_DIR, exist_ok=True)

CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
def load_saved_token() -> str:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f).get("token", "")
        except Exception:
            return ""
    return ""

def save_token(token: str):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"token": token}, f)

class TokenModal(ModalScreen[str]):
    CSS = """
    TokenModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.6);
    }
    #modal-content {
        width: 60;
        height: auto;
        background: #1e1e1e;
        border: thick cyan;
        padding: 1 2;
    }
    #modal-content Label {
        margin-bottom: 1;
        content-align: center middle;
        width: 100%;
    }
    #modal-content Input {
        margin-bottom: 1;
        background: #111;
        border: solid $accent;
    }
    #modal-content Button {
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-content"):
            yield Label("[bold magenta]Discord Bot Token[/bold magenta]")
            yield Input(placeholder="Paste token here...", id="token-input", password=True)
            yield Button("Cancel", variant="default", id="cancel-btn")
            yield Button("Save", variant="primary", id="save-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self.submit_token()
        if event.button.id == "cancel-btn":
            self.dismiss()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.submit_token()

    def submit_token(self) -> None:
        token_val = self.query_one("#token-input", Input).value.strip()
        if token_val:
            self.dismiss(token_val)

class ChatInput(Input):
    BINDINGS = [
        Binding("up", "history_up", "Previous Command", show=False),
        Binding("down", "history_down", "Next Command", show=False),
        Binding("tab", "autocomplete", "Autocomplete", show=False)
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.history = []
        self.history_index = -1

    def action_history_up(self) -> None:
        if not self.history: return
        if self.history_index == -1: self.history_index = len(self.history) - 1
        elif self.history_index > 0: self.history_index -= 1
        self.value = self.history[self.history_index]

    def action_history_down(self) -> None:
        if self.history_index == -1: return
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.value = self.history[self.history_index]
        else:
            self.history_index = -1
            self.value = ""

    def action_autocomplete(self) -> None:
        current_text = self.value.strip()
        if not current_text: return
        app = self.app
        
        if current_text.startswith("/server "):
            query = current_text[8:].lower()
            matches = [g.name for g in app.discord_client.guilds if g.name.lower().startswith(query)]
            if matches: self.value = f"/server {matches[0]}"
        elif current_text.startswith("/channel ") and app.active_guild:
            query = current_text[9:].lower().replace("#", "")
            matches = [c.name for c in app.active_guild.text_channels if c.name.lower().startswith(query)]
            if matches: self.value = f"/channel #{matches[0]}"
        elif current_text.startswith("/"):
            query = current_text[1:].lower()
            cmds = ["help", "server", "channel", "dm", "react", "reply", "edit", "delete", "upload", "leave"]
            matches = [c for c in cmds if c.startswith(query)]
            if matches: self.value = f"/{matches[0]} "


class DistordApp(App):
    BINDINGS = [
        Binding("ctrl+t", "change_token", "Change Token", show=True),
    ]
    CSS = """
    Screen { background: #1a1a1a; }
    #main-layout { height: 1fr; }
    .sidebar {
        width: 22%;
        border-right: solid $accent;
        padding: 1;
        background: #151515;
    }
    #chat-area { width: 56%; padding: 1; }
    #prompt-container { dock: bottom; height: auto; border-top: solid $accent; }
    ChatInput { background: transparent; border: none; }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = ""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True 
        self.discord_client = discord.Client(intents=intents)
        
        self.active_guild = None
        self.active_channel = None
        self.msg_map = {}
        self.next_local_id = 1000

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-layout"):
            with Vertical(classes="sidebar"):
                yield Label("[bold magenta]CONTEXTS[/bold magenta]\n", id="servers-sidebar")
            with Vertical(classes="sidebar"):
                yield Label("[bold cyan]CHANNELS[/bold cyan]\n", id="channels-sidebar")
            with Vertical(id="chat-area"):
                yield RichLog(id="chat-log", max_lines=2000, wrap=True)
        
        with Horizontal(id="prompt-container"):
            yield ChatInput(placeholder="Connecting...", id="cmd-input")
        yield Footer()

    def on_mount(self) -> None:
        saved = load_saved_token()
        if saved:
            self.token = saved
            self.run_worker(self.start_discord_client(), group="discord")
        else:
            self.action_change_token()

    def action_change_token(self) -> None:
        def handle_new_token(new_token: str | None) -> None:
            if not new_token: 
                return
            
            save_token(new_token)
            self.token = new_token
            
            asyncio.create_task(self.hot_reboot_client())

        self.push_screen(TokenModal(), callback=handle_new_token)

    async def hot_reboot_client(self):
        chat = self.query_one("#chat-log", RichLog)
        chat.write(Text.from_markup("[System] [yellow]Tearing down client connections for swap...[/yellow]"))
        
        try:
            await self.discord_client.close()
        except Exception:
            pass

        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True 
        self.discord_client = discord.Client(intents=intents)
        
        self.run_worker(self.start_discord_client(), group="discord")

    async def start_discord_client(self):
        chat = self.query_one("#chat-log", RichLog)

        @self.discord_client.event
        async def on_ready():
            chat.write(Text.from_markup(f"[System] Connected as: [bold green]{self.discord_client.user.name}[/bold green]"))
            self.update_sidebars()
            if self.discord_client.guilds:
                await self.switch_guild(self.discord_client.guilds[0])

        @self.discord_client.event
        async def on_message(message):
            if self.active_channel and message.channel.id == self.active_channel.id:
                self.render_incoming_message(message)

        @self.discord_client.event
        async def on_message_edit(before, after):
            if self.active_channel and after.channel.id == self.active_channel.id:
                loc_id = next((k for k, v in self.msg_map.items() if v.id == after.id), None)
                if loc_id:
                    self.msg_map[loc_id] = after
                await self.refresh_chat_display()

        @self.discord_client.event
        async def on_message_delete(message):
            if self.active_channel and message.channel.id == self.active_channel.id:
                loc_id = next((k for k, v in self.msg_map.items() if v.id == message.id), None)
                if loc_id:
                    del self.msg_map[loc_id]
                await self.refresh_chat_display()

        try:
            await self.discord_client.start(self.token)
        except Exception as e:
            chat.write(Text.from_markup(f"[bold red][Error] Gateway crash: {e}[/bold red]"))

    # UI DISPLAY LOGIC

    async def refresh_chat_display(self):
        chat = self.query_one("#chat-log", RichLog)
        chat.clear()
        
        for loc_id in sorted(self.msg_map.keys()):
            msg = self.msg_map[loc_id]
            
            if msg.reference and msg.reference.message_id:
                chat.write(Text.from_markup("    ↳ [dim]Reply to reference thread[/dim]"))

            author_name = msg.author.name if msg.author else "Unknown User"
            author_style = f"[bold green]{self.discord_client.user.name}[/bold green]" if msg.author == self.discord_client.user else f"[bold cyan]{author_name}[/bold cyan]"
            edited_tag = " [yellow](edited)[/yellow]" if msg.edited_at else ""
            
            chat.write(Text.from_markup(f"[{loc_id}] {author_style}{edited_tag}: {msg.content}"))
            
            for attach in msg.attachments:
                icon = "📷" if attach.content_type and attach.content_type.startswith("image/") else "📄"
                chat.write(Text.from_markup(f"      {icon} [dim]{attach.filename} -> [bold underline blue]{attach.url}[/bold underline blue][/dim]"))

    def update_sidebars(self):
        server_lbl = self.query_one("#servers-sidebar", Label)
        text = "[bold magenta]SERVERS/DMS[/bold magenta]\n\n"
        
        dm_marker = "> " if self.active_guild is None else "  "
        text += f"{dm_marker}Direct Messages\n"
        
        for guild in self.discord_client.guilds:
            marker = "> " if self.active_guild and guild.id == self.active_guild.id else "  "
            text += f"{marker}{guild.name}\n"
        server_lbl.update(text)

    def update_channel_sidebar(self):
        chan_lbl = self.query_one("#channels-sidebar", Label)
        text = "[bold cyan]CHANNELS[/bold cyan]\n\n"
        
        if self.active_guild is None:
            text = "[bold cyan]ACTIVE DMS[/bold cyan]\n\n"
            dms = [c for c in self.discord_client.private_channels if isinstance(c, discord.DMChannel)]
            for dm in dms:
                marker = "> " if self.active_channel and dm.id == self.active_channel.id else "  "
                recipient_name = dm.recipient.name if dm.recipient else f"DM Channel ({dm.id})"
                text += f"{marker}@{recipient_name}\n"
        else:
            for chan in self.active_guild.text_channels:
                marker = "> " if self.active_channel and chan.id == self.active_channel.id else "  "
                text += f"{marker}#{chan.name}\n"
        chan_lbl.update(text)

    def render_incoming_message(self, message: discord.Message):
        loc_id = next((k for k, v in self.msg_map.items() if v.id == message.id), None)
        if not loc_id:
            loc_id = self.next_local_id
            self.msg_map[loc_id] = message
            self.next_local_id += 1

        chat = self.query_one("#chat-log", RichLog)
        if message.reference and message.reference.message_id:
            chat.write(Text.from_markup("    ↳ [dim]Reply to reference thread[/dim]"))

        author_name = message.author.name if message.author else "Unknown User"
        author_style = f"[bold green]{self.discord_client.user.name}[/bold green]" if message.author == self.discord_client.user else f"[bold cyan]{author_name}[/bold cyan]"
        edited_tag = " [yellow](edited)[/yellow]" if message.edited_at else ""
        
        chat.write(Text.from_markup(f"[{loc_id}] {author_style}{edited_tag}: {message.content}"))

        for attach in message.attachments:
            icon = "📷" if attach.content_type and attach.content_type.startswith("image/") else "📄"
            chat.write(Text.from_markup(f"      {icon} [dim]{attach.filename} -> [bold underline blue]{attach.url}[/bold underline blue][/dim]"))

    async def switch_guild(self, guild: discord.Guild):
        self.active_guild = guild
        self.update_sidebars()
        if guild and guild.text_channels:
            await self.switch_channel(guild.text_channels[0])
        else:
            self.active_channel = None
            self.update_channel_sidebar()

    async def switch_channel(self, channel):
        self.active_channel = channel
        self.update_channel_sidebar()
        self.msg_map.clear() 
        
        prompt = self.query_one("#cmd-input", ChatInput)
        if isinstance(channel, discord.DMChannel):
            r_name = channel.recipient.name if channel.recipient else "Unknown"
            prompt.placeholder = f"Discord:/DMs/{r_name}>"
        else:
            prompt.placeholder = f"Discord:/Servers/{self.active_guild.name}/{channel.name}>"

        try:
            async for msg in channel.history(limit=30, oldest_first=True):
                self.render_incoming_message(msg)
        except Exception as e:
            self.query_one("#chat-log", RichLog).write(f"[System Error] History loading failed: {e}")

    # INPUT OPERATIONS

    def on_input_submitted(self, event: ChatInput.Submitted) -> None:
        text = event.value.strip()
        if not text: return

        cmd_input = self.query_one("#cmd-input", ChatInput)
        cmd_input.history.append(text)
        cmd_input.history_index = -1

        if text.startswith("/"):
            asyncio.create_task(self.handle_command(text))
        else:
            if self.active_channel:
                asyncio.create_task(self.active_channel.send(text))
        cmd_input.value = ""

    async def handle_command(self, raw_cmd: str):
        chat = self.query_one("#chat-log", RichLog)
        parts = raw_cmd[1:].split(" ", 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "help":
            chat.write(Text.from_markup("\n[bold blue]Distord v0.1.0[/bold blue]"))
            chat.write("  /server <name>     - Jump to server workspace context [Use 'dms' for Direct Messages]")
            chat.write("  /channel <name>    - Switch channel scope context path")
            chat.write("  /dm <username>     - Open a direct DM channel thread with a user")
            chat.write("  /upload <filepath> - Upload a local file/image (Max 10MB)")
            chat.write("  /react <id> <emoji>- Post reaction payload directly to tracking index")
            chat.write("  /reply <id> <text> - Chain inline threading text reply directly to target index")
            chat.write("  /edit <id> <text>  - Edit a tracking message context sent by this engine client")
            chat.write("  /delete <id>       - Purge structural tracking record message out of history live\n")

        elif cmd == "server":
            if args.lower() in ["dms", "Direct Messages"]:
                self.active_guild = None
                self.update_sidebars()
                dms = [
                    c for c in self.discord_client.private_channels
                    if isinstance(c, discord.DMChannel)
                ]
                if dms:
                    chat.clear()
                    await self.switch_channel(dms[0])
                else: self.update_channel_sidebar()
            else:
                target = discord.utils.get(self.discord_client.guilds, name=args)
                if target:
                    chat.clear()
                    await self.switch_guild(target)

        elif cmd == "channel":
            if self.active_guild:
                target = discord.utils.get(self.active_guild.text_channels, name=args.replace("#", ""))
                if target:
                    chat.clear() 
                    await self.switch_channel(target)
            else:
                dms = [c for c in self.discord_client.private_channels if isinstance(c, discord.DMChannel)]
                target = next((d for d in dms if d.recipient and d.recipient.name.lower() == args.replace("@", "").lower()), None)
                if target:
                    chat.clear() 
                    await self.switch_channel(target)

        elif cmd == "dm":
            if not self.active_guild:
                chat.write("[System] You must be inside a server context to target a user profile link.")
                return
            member = discord.utils.get(self.active_guild.members, name=args)
            if member:
                chat.clear()
                chat.write(f"[System] DM Pipeline with @{member.name}...")
                dm_channel = await member.create_dm()
                self.active_guild = None
                self.update_sidebars()
                await self.switch_channel(dm_channel)
            else:
                chat.write(f"[System Error] Could not find member '{args}' inside this server layout tree.")

        elif cmd == "upload":
            if not self.active_channel:
                chat.write("[System Error] No active channel context selected to drop file attachment payload.")
                return
            
            filepath = args.strip('"').strip("'")
            if not os.path.exists(filepath):
                chat.write(f"[System Error] File system path not found: {filepath}")
                return
                                           # 10 mb
            if os.path.getsize(filepath) > 10485760:
                chat.write("[System Error] Upload rejected. Payload breaks the maximum structural limit of 10MB.")
                return

            try:
                chat.write(f"[System] Syncing and uploading asset: {os.path.basename(filepath)}...")
                discord_file = discord.File(filepath)
                await self.active_channel.send(file=discord_file)
            except Exception as e:
                chat.write(f"[System Error] File dispatch payload architecture failed: {e}")

        elif cmd == "react":
            try:
                sub = args.split(" ", 1)
                loc_id, emoji = int(sub[0]), sub[1]
                if loc_id in self.msg_map: await self.msg_map[loc_id].add_reaction(emoji)
            except: pass

        elif cmd == "reply":
            try:
                sub = args.split(" ", 1)
                loc_id, payload = int(sub[0]), sub[1]
                if loc_id in self.msg_map: await self.msg_map[loc_id].reply(payload)
            except: pass

        elif cmd == "edit":
            try:
                sub = args.split(" ", 1)
                loc_id, payload = int(sub[0]), sub[1]
                if loc_id in self.msg_map and self.msg_map[loc_id].author == self.discord_client.user:
                    await self.msg_map[loc_id].edit(content=payload)
            except: pass

        elif cmd == "delete":
            try:
                loc_id = int(args)
                if loc_id in self.msg_map: await self.msg_map[loc_id].delete()
            except: pass

        elif cmd == "leave":
            await self.discord_client.close()
            self.exit()

    async def on_unmount(self) -> None:
        await self.discord_client.close()

if __name__ == "__main__":
    distord = DistordApp()
    distord.run()