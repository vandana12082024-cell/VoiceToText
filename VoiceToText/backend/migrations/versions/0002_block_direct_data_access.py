"""Restrict direct Supabase Data API access; FastAPI owns database authorization."""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    # The API uses the Postgres owner connection and filters by validated user ID.
    # No direct-access policies are needed by the mobile app (it uses Auth only).
    op.execute("ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.transcriptions ENABLE ROW LEVEL SECURITY")


def downgrade():
    op.execute("ALTER TABLE public.transcriptions DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.user_preferences DISABLE ROW LEVEL SECURITY")
