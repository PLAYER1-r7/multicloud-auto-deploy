"""AWS Lambda エントリーポイント（大学入試解答専用）"""

from app.main import app
from mangum import Mangum

# Lambda handler
handler = Mangum(app, lifespan="off")
