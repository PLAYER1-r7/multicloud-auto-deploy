"""Simple SNS - Complete Python Frontend with Reflex."""

import reflex as rx
import httpx
from typing import List, Optional
from pydantic import BaseModel
import os

# API URL from environment variable or default
API_URL = os.getenv("API_URL", "http://localhost:8000")


class Message(BaseModel):
    """Message model."""
    id: str
    content: str
    author: str
    image_url: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


class State(rx.State):
    """Application state."""
    
    # Message list
    messages: List[Message] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    
    # Form inputs
    content: str = ""
    author: str = ""
    
    # Edit mode
    editing_id: Optional[str] = None
    edit_content: str = ""
    edit_author: str = ""
    
    # Image upload
    selected_image: Optional[str] = None
    image_url: Optional[str] = None
    uploading: bool = False
    loading: bool = False

    async def load_messages(self):
        """Load messages from API."""
        try:
            async with httpx.AsyncClient() as client:
                api_url = os.getenv("API_URL", "http://localhost:8000")
                response = await client.get(
                    f"{api_url}/api/messages/",
                    params={"page": self.page, "page_size": self.page_size},
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    self.messages = [Message(**msg) for msg in data["messages"]]
                    self.total = data["total"]
        except Exception as e:
            print(f"Error loading messages: {e}")
            import traceback
            traceback.print_exc()

    async def create_message(self):
        """Create a new message."""
        if not self.content.strip() or not self.author.strip():
            return
        
        self.loading = True
        try:
            async with httpx.AsyncClient() as client:
                api_url = os.getenv("API_URL", "http://localhost:8000")
                url = f"{api_url}/api/messages/"
                print(f"Posting to: {url}")  # Debug log
                response = await client.post(
                    url,
                    json={
                        "content": self.content,
                        "author": self.author,
                        "image_url": self.image_url
                    },
                    timeout=10.0
                )
                print(f"Response status: {response.status_code}")  # Debug log
                if response.status_code in [200, 201]:  # Accept both OK and Created
                    self.content = ""
                    self.author = ""
                    self.image_url = None
                    self.selected_image = None
                    await self.load_messages()
                else:
                    print(f"Error response: {response.text}")
        except Exception as e:
            print(f"Error creating message: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.loading = False

    async def delete_message(self, message_id: str):
        """Delete a message."""
        try:
            async with httpx.AsyncClient() as client:
                api_url = os.getenv("API_URL", "http://localhost:8000")
                response = await client.delete(
                    f"{api_url}/api/messages/{message_id}",
                    timeout=10.0
                )
                if response.status_code in [200, 204]:  # Accept OK or No Content
                    await self.load_messages()
        except Exception as e:
            print(f"Error deleting message: {e}")
            import traceback
            traceback.print_exc()

    def start_edit(self, message: Message):
        """Start editing a message."""
        self.editing_id = message.id
        self.edit_content = message.content
        self.edit_author = message.author

    def cancel_edit(self):
        """Cancel editing."""
        self.editing_id = None
        self.edit_content = ""
        self.edit_author = ""

    async def save_edit(self, message_id: str):
        """Save edited message."""
        if not self.edit_content.strip() or not self.edit_author.strip():
            return
        
        try:
            async with httpx.AsyncClient() as client:
                api_url = os.getenv("API_URL", "http://localhost:8000")
                response = await client.put(
                    f"{api_url}/api/messages/{message_id}",
                    json={
                        "content": self.edit_content,
                        "author": self.edit_author
                    },
                    timeout=10.0
                )
                if response.status_code in [200, 201]:  # Accept OK or Created
                    self.editing_id = None
                    self.edit_content = ""
                    self.edit_author = ""
                    await self.load_messages()
        except Exception as e:
            print(f"Error updating message: {e}")
            import traceback
            traceback.print_exc()

    async def upload_image(self, files: List[rx.UploadFile]):
        """Upload an image file."""
        if not files:
            return
        
        self.uploading = True
        try:
            file = files[0]
            file_data = await file.read()
            
            async with httpx.AsyncClient() as client:
                api_url = os.getenv("API_URL", "http://localhost:8000")
                response = await client.post(
                    f"{api_url}/api/uploads/",
                    files={"file": (file.filename, file_data, file.content_type)},
                    timeout=30.0
                )
                if response.status_code in [200, 201]:  # Accept OK or Created
                    data = response.json()
                    self.image_url = data["url"]
                    self.selected_image = data["url"]
        except Exception as e:
            print(f"Error uploading image: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.uploading = False

    def remove_image(self):
        """Remove selected image."""
        self.selected_image = None
        self.image_url = None

    async def next_page(self):
        """Go to next page."""
        if self.page * self.page_size < self.total:
            self.page += 1
            await self.load_messages()

    async def prev_page(self):
        """Go to previous page."""
        if self.page > 1:
            self.page -= 1
            await self.load_messages()


def message_form() -> rx.Component:
    """Message creation form."""
    return rx.box(
        rx.heading("新規メッセージ", size="7", margin_bottom="1em"),
        rx.vstack(
            rx.text_area(
                placeholder="メッセージを入力...",
                value=State.content,
                on_change=State.set_content,
                width="100%",
                rows="4",
            ),
            rx.input(
                placeholder="名前",
                value=State.author,
                on_change=State.set_author,
                width="100%",
            ),
            rx.hstack(
                rx.button(
                    "送信",
                    on_click=State.create_message,
                    loading=State.loading,
                    color_scheme="blue",
                ),
                width="100%",
                justify="end",
            ),
            rx.divider(),
            rx.vstack(
                rx.upload(
                    rx.button(
                        rx.icon("image", size=18),
                        rx.text("画像を選択", margin_left="0.5em"),
                        color_scheme="gray",
                    ),
                    on_drop=State.upload_image,
                    accept={"image/*": [".png", ".jpg", ".jpeg", ".gif"]},
                    max_files=1,
                ),
                rx.cond(
                    State.selected_image,
                    rx.box(
                        rx.image(src=State.selected_image, max_width="300px", border_radius="8px"),
                        rx.button(
                            rx.icon("x", size=16),
                            on_click=State.remove_image,
                            size="1",
                            color_scheme="red",
                            position="absolute",
                            top="5px",
                            right="5px",
                        ),
                        position="relative",
                        display="inline-block",
                        margin_top="1em",
                    ),
                ),
                width="100%",
                align="start",
            ),
            spacing="3",
            width="100%",
        ),
        padding="2em",
        background="white",
        border_radius="8px",
        box_shadow="0 2px 4px rgba(0,0,0,0.1)",
    )


def message_card(message: Message) -> rx.Component:
    """Message display card."""
    return rx.cond(
        State.editing_id == message.id,
        # Edit mode
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.input(
                        value=State.edit_author,
                        on_change=State.set_edit_author,
                        placeholder="名前",
                        width="200px",
                    ),
                    rx.text(
                        message.created_at,
                        color="gray",
                        size="2",
                    ),
                    justify="between",
                    width="100%",
                ),
                rx.text_area(
                    value=State.edit_content,
                    on_change=State.set_edit_content,
                    placeholder="メッセージ内容",
                    width="100%",
                    rows="4",
                ),
                rx.hstack(
                    rx.button("保存", on_click=lambda: State.save_edit(message.id), color_scheme="blue"),
                    rx.button("キャンセル", on_click=State.cancel_edit, color_scheme="gray"),
                    spacing="2",
                ),
                spacing="3",
                width="100%",
            ),
            padding="1.5em",
            background="white",
            border_radius="8px",
            border="1px solid #e5e7eb",
        ),
        # View mode
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.hstack(
                        rx.text(message.author, weight="bold", size="3"),
                        rx.text(
                            message.created_at,
                            color="gray",
                            size="2",
                        ),
                        spacing="3",
                    ),
                    rx.hstack(
                        rx.button(
                            rx.icon("pencil", size=16),
                            on_click=lambda: State.start_edit(message),
                            size="1",
                            color_scheme="blue",
                            variant="ghost",
                        ),
                        rx.button(
                            rx.icon("trash-2", size=16),
                            on_click=lambda: State.delete_message(message.id),
                            size="1",
                            color_scheme="red",
                            variant="ghost",
                        ),
                        spacing="2",
                    ),
                    justify="between",
                    width="100%",
                ),
                rx.text(message.content, size="3", margin_top="0.5em"),
                rx.cond(
                    message.image_url,
                    rx.image(
                        src=message.image_url,
                        max_width="500px",
                        border_radius="8px",
                        margin_top="1em",
                    ),
                ),
                spacing="2",
                width="100%",
                align="start",
            ),
            padding="1.5em",
            background="white",
            border_radius="8px",
            border="1px solid #e5e7eb",
            _hover={"background": "#f9fafb"},
        ),
    )


def message_list() -> rx.Component:
    """Message list with pagination."""
    return rx.box(
        rx.heading("メッセージ一覧", size="7", margin_bottom="1em"),
        rx.cond(
            State.messages.length() == 0,
            rx.text("まだメッセージがありません", color="gray", text_align="center", padding="3em"),
            rx.vstack(
                rx.foreach(State.messages, message_card),
                spacing="4",
                width="100%",
            ),
        ),
        rx.hstack(
            rx.button(
                rx.icon("chevron-left", size=16),
                "前へ",
                on_click=State.prev_page,
                disabled=State.page == 1,
                color_scheme="blue",
                variant="soft",
            ),
            rx.text(f"ページ {State.page}", size="3"),
            rx.button(
                "次へ",
                rx.icon("chevron-right", size=16),
                on_click=State.next_page,
                disabled=State.page * State.page_size >= State.total,
                color_scheme="blue",
                variant="soft",
            ),
            spacing="4",
            justify="center",
            margin_top="2em",
        ),
        padding="2em",
        background="white",
        border_radius="8px",
        box_shadow="0 2px 4px rgba(0,0,0,0.1)",
    )


def index() -> rx.Component:
    """Main page."""
    return rx.container(
        rx.vstack(
            rx.heading(
                "Simple SNS",
                size="9",
                margin_top="1em",
                margin_bottom="1em",
                text_align="center",
            ),
            rx.grid(
                message_form(),
                message_list(),
                columns="1",
                spacing="6",
                width="100%",
            ),
            spacing="6",
            padding_y="2em",
        ),
        size="3",
    )


app = rx.App(
    theme=rx.theme(
        appearance="light",
        accent_color="blue",
    )
)
app.add_page(index, on_load=State.load_messages)
