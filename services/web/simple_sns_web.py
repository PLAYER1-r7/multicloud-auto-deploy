"""Simple SNS Web - Reflex Frontend"""
import reflex as rx
from datetime import datetime
from typing import List
import httpx
import os


# 環境変数からAPIエンドポイントを取得
API_URL = os.getenv("API_URL", "http://localhost:8000")


class Message(rx.Base):
    """メッセージモデル"""
    id: str
    content: str
    author: str
    image_url: str | None = None
    created_at: datetime


class State(rx.State):
    """アプリケーション状態"""
    
    # メッセージリスト
    messages: List[Message] = []
    
    # フォーム入力
    new_content: str = ""
    new_author: str = ""
    
    # UI状態
    is_loading: bool = False
    error_message: str = ""
    success_message: str = ""
    
    async def load_messages(self):
        """メッセージを読み込み"""
        self.is_loading = True
        self.error_message = ""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{API_URL}/api/messages")
                response.raise_for_status()
                data = response.json()
                
                # メッセージを新しい順に並べ替え
                self.messages = [
                    Message(**msg) for msg in data.get("messages", [])
                ]
                
        except Exception as e:
            self.error_message = f"メッセージの読み込みに失敗しました: {str(e)}"
        finally:
            self.is_loading = False
    
    async def post_message(self):
        """メッセージを投稿"""
        if not self.new_content or not self.new_author:
            self.error_message = "内容と投稿者名を入力してください"
            return
        
        self.is_loading = True
        self.error_message = ""
        self.success_message = ""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_URL}/api/messages",
                    json={
                        "content": self.new_content,
                        "author": self.new_author,
                    }
                )
                response.raise_for_status()
                
                # 成功メッセージ
                self.success_message = "メッセージを投稿しました！"
                
                # フォームをクリア
                self.new_content = ""
                self.new_author = ""
                
                # メッセージを再読み込み
                await self.load_messages()
                
        except Exception as e:
            self.error_message = f"投稿に失敗しました: {str(e)}"
        finally:
            self.is_loading = False
    
    def set_content(self, value: str):
        """内容を設定"""
        self.new_content = value
        self.error_message = ""
        self.success_message = ""
    
    def set_author(self, value: str):
        """投稿者名を設定"""
        self.new_author = value
        self.error_message = ""
        self.success_message = ""


def navbar() -> rx.Component:
    """ナビゲーションバー"""
    return rx.box(
        rx.hstack(
            rx.heading("🐍 Simple SNS", size="lg"),
            rx.spacer(),
            rx.badge("Python Full Stack", color_scheme="green"),
            width="100%",
            padding="1rem",
        ),
        bg="blue.600",
        color="white",
        width="100%",
    )


def message_card(message: Message) -> rx.Component:
    """メッセージカード"""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.avatar(name=message.author, size="md"),
                rx.vstack(
                    rx.text(message.author, font_weight="bold"),
                    rx.text(
                        message.created_at.strftime("%Y-%m-%d %H:%M"),
                        font_size="sm",
                        color="gray.500",
                    ),
                    align_items="start",
                    spacing="0",
                ),
                align_items="center",
                width="100%",
            ),
            rx.text(message.content, padding_top="0.5rem"),
            rx.cond(
                message.image_url,
                rx.image(
                    src=message.image_url,
                    max_width="300px",
                    border_radius="md",
                ),
            ),
            align_items="start",
            width="100%",
        ),
        padding="1rem",
        border_radius="lg",
        border="1px solid",
        border_color="gray.200",
        bg="white",
        _hover={"box_shadow": "md"},
        transition="all 0.2s",
    )


def message_form() -> rx.Component:
    """メッセージ投稿フォーム"""
    return rx.box(
        rx.vstack(
            rx.heading("メッセージを投稿", size="md", margin_bottom="1rem"),
            
            # エラーメッセージ
            rx.cond(
                State.error_message != "",
                rx.alert(
                    rx.alert_icon(),
                    rx.alert_title(State.error_message),
                    status="error",
                    margin_bottom="1rem",
                ),
            ),
            
            # 成功メッセージ
            rx.cond(
                State.success_message != "",
                rx.alert(
                    rx.alert_icon(),
                    rx.alert_title(State.success_message),
                    status="success",
                    margin_bottom="1rem",
                ),
            ),
            
            # 投稿者名
            rx.form_control(
                rx.form_label("投稿者名"),
                rx.input(
                    placeholder="あなたの名前",
                    value=State.new_author,
                    on_change=State.set_author,
                    is_disabled=State.is_loading,
                ),
                is_required=True,
            ),
            
            # メッセージ内容
            rx.form_control(
                rx.form_label("メッセージ"),
                rx.text_area(
                    placeholder="メッセージを入力してください...",
                    value=State.new_content,
                    on_change=State.set_content,
                    rows=4,
                    is_disabled=State.is_loading,
                ),
                is_required=True,
            ),
            
            # 投稿ボタン
            rx.button(
                "投稿する",
                on_click=State.post_message,
                is_loading=State.is_loading,
                color_scheme="blue",
                width="100%",
            ),
            
            width="100%",
            spacing="1rem",
        ),
        padding="1.5rem",
        border_radius="lg",
        border="1px solid",
        border_color="gray.200",
        bg="white",
    )


def message_list() -> rx.Component:
    """メッセージリスト"""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.heading("メッセージ一覧", size="md"),
                rx.spacer(),
                rx.button(
                    "更新",
                    on_click=State.load_messages,
                    is_loading=State.is_loading,
                    size="sm",
                ),
                width="100%",
                margin_bottom="1rem",
            ),
            
            # ローディング
            rx.cond(
                State.is_loading,
                rx.center(
                    rx.spinner(size="lg"),
                    padding="2rem",
                ),
            ),
            
            # メッセージが空
            rx.cond(
                (State.messages.length() == 0) & ~State.is_loading,
                rx.center(
                    rx.text("まだメッセージがありません", color="gray.500"),
                    padding="2rem",
                ),
            ),
            
            # メッセージリスト
            rx.foreach(
                State.messages,
                message_card,
            ),
            
            width="100%",
            spacing="1rem",
        ),
        padding="1.5rem",
    )


def index() -> rx.Component:
    """メインページ"""
    return rx.fragment(
        navbar(),
        rx.container(
            rx.vstack(
                # 投稿フォーム
                message_form(),
                
                # メッセージリスト
                message_list(),
                
                width="100%",
                spacing="2rem",
                padding_y="2rem",
            ),
            max_width="800px",
        ),
    )


# アプリケーション設定
app = rx.App(
    theme=rx.theme(
        appearance="light",
        accent_color="blue",
    )
)

# ページ追加（初回ロード時にメッセージを読み込み）
app.add_page(
    index,
    title="Simple SNS - Python Full Stack",
    on_load=State.load_messages,
)
