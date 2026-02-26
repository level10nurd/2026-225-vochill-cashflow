"""Configuration management for VoChill cash flow system"""

import os
from pathlib import Path
from typing import Any, Dict
import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_DIR = DATA_DIR / "config"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
SRC_DIR = PROJECT_ROOT / "src"
QUERIES_DIR = SRC_DIR / "queries"

# Ensure directories exist
for dir_path in [RAW_DATA_DIR, PROCESSED_DATA_DIR, OUTPUT_DIR, QUERIES_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)


class Config:
    """Configuration manager for VoChill cash flow system"""

    def __init__(self):
        self.gcp_project_id = os.getenv("GCP_PROJECT_ID", "vochill")
        self.gcp_credentials_path = os.getenv("GCP_CREDENTIALS_PATH")
        self.bigquery_dataset = os.getenv("BIGQUERY_DATASET", "revrec")
        self.bigquery_location = os.getenv("BIGQUERY_LOCATION", "US")

        # Load configuration files
        self.cash_flow_categories = self._load_yaml(CONFIG_DIR / "cash_flow_categories.yaml")
        self.payment_timing = self._load_yaml(CONFIG_DIR / "payment_timing.yaml")

    @staticmethod
    def _load_yaml(file_path: Path) -> Dict[str, Any]:
        """Load YAML configuration file"""
        if not file_path.exists():
            return {}

        with open(file_path, 'r') as f:
            return yaml.safe_load(f) or {}

    def get_bigquery_table(self, table_name: str) -> str:
        """Get fully qualified BigQuery table name"""
        return f"{self.gcp_project_id}.{self.bigquery_dataset}.{table_name}"


# Global config instance
config = Config()
