from dotenv import load_dotenv

# Loads .env into the process environment on first import, so adapters'
# require_env() calls actually see it. Never overrides a variable
# already set in the real environment (e.g. by a shell or CI) — .env
# only fills in what isn't already there.
load_dotenv()

from .distribution_agent import ApprovalCallback, cli_approval, distribute, DistributionRecord

__all__ = ["distribute", "DistributionRecord", "ApprovalCallback", "cli_approval"]
