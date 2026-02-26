"""BigQuery connector for VoChill cash flow system"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
from google.api_core import retry

from ..config import config


class BigQueryConnector:
    """
    BigQuery client for accessing VoChill data warehouse.

    Handles authentication, query execution, and DataFrame conversion
    for the vochill.revrec dataset.
    """

    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize BigQuery connector.

        Args:
            credentials_path: Path to GCP service account JSON key file.
                            If None, uses GCP_CREDENTIALS_PATH from environment.
        """
        self.project_id = config.gcp_project_id
        self.dataset = config.bigquery_dataset
        self.location = config.bigquery_location

        # Set up credentials
        creds_path = credentials_path or config.gcp_credentials_path
        if creds_path and Path(creds_path).exists():
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            self.client = bigquery.Client(
                credentials=credentials,
                project=self.project_id,
                location=self.location,
            )
        else:
            # Use Application Default Credentials (for Hex environment)
            self.client = bigquery.Client(
                project=self.project_id,
                location=self.location,
            )

    def query(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        use_legacy_sql: bool = False,
    ) -> pd.DataFrame:
        """
        Execute a SQL query and return results as DataFrame.

        Args:
            sql: SQL query string
            params: Optional query parameters for parameterized queries
            use_legacy_sql: Whether to use legacy SQL (default: False, uses Standard SQL)

        Returns:
            pandas DataFrame with query results

        Example:
            >>> bq = BigQueryConnector()
            >>> df = bq.query("SELECT * FROM deposits WHERE platform = 'Amazon' LIMIT 10")
        """
        job_config = bigquery.QueryJobConfig(use_legacy_sql=use_legacy_sql)

        # Add query parameters if provided
        if params:
            job_config.query_parameters = [
                bigquery.ScalarQueryParameter(key, "STRING", value)
                for key, value in params.items()
            ]

        # Execute query with retry logic
        query_job = self.client.query(sql, job_config=job_config)

        # Convert to DataFrame
        df = query_job.to_dataframe()

        return df

    def get_table_data(
        self,
        table_name: str,
        columns: Optional[List[str]] = None,
        where: Optional[str] = None,
        limit: Optional[int] = None,
        order_by: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch data from a table with optional filtering.

        Args:
            table_name: Name of the table (e.g., "deposits", "orders")
            columns: List of columns to select (default: all columns)
            where: WHERE clause condition (without "WHERE" keyword)
            limit: Maximum number of rows to return
            order_by: ORDER BY clause (without "ORDER BY" keyword)

        Returns:
            pandas DataFrame with table data

        Example:
            >>> bq = BigQueryConnector()
            >>> df = bq.get_table_data(
            ...     "deposits",
            ...     columns=["platform", "date_time", "total"],
            ...     where="platform = 'Amazon'",
            ...     limit=1000
            ... )
        """
        # Build column list
        cols = ", ".join(columns) if columns else "*"

        # Build WHERE clause
        where_clause = f"WHERE {where}" if where else ""

        # Build ORDER BY clause
        order_clause = f"ORDER BY {order_by}" if order_by else ""

        # Build LIMIT clause
        limit_clause = f"LIMIT {limit}" if limit else ""

        # Build full query
        sql = f"""
        SELECT {cols}
        FROM {config.get_bigquery_table(table_name)}
        {where_clause}
        {order_clause}
        {limit_clause}
        """

        return self.query(sql)

    def get_deposits(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        platform: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch deposit data (revenue) from BigQuery.

        Args:
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            platform: Filter by platform (Amazon, Shopify, etc.)

        Returns:
            DataFrame with deposit transactions
        """
        conditions = []

        if start_date:
            conditions.append(f"DATE(date_time) >= '{start_date}'")
        if end_date:
            conditions.append(f"DATE(date_time) <= '{end_date}'")
        if platform:
            conditions.append(f"platform = '{platform}'")

        where_clause = " AND ".join(conditions) if conditions else None

        return self.get_table_data(
            "deposits",
            where=where_clause,
            order_by="date_time"
        )

    def get_orders(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        platform: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch order data from BigQuery.

        Args:
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            platform: Filter by platform (Amazon, Shopify, etc.)

        Returns:
            DataFrame with order transactions
        """
        conditions = []

        if start_date:
            conditions.append(f"DATE(date_time) >= '{start_date}'")
        if end_date:
            conditions.append(f"DATE(date_time) <= '{end_date}'")
        if platform:
            conditions.append(f"platform = '{platform}'")

        where_clause = " AND ".join(conditions) if conditions else None

        return self.get_table_data(
            "orders",
            where=where_clause,
            order_by="date_time"
        )

    def get_fees(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        platform: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch platform fee data from BigQuery.

        Args:
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            platform: Filter by platform (Amazon, Shopify, etc.)

        Returns:
            DataFrame with fee transactions
        """
        conditions = []

        if start_date:
            conditions.append(f"DATE(date_time) >= '{start_date}'")
        if end_date:
            conditions.append(f"DATE(date_time) <= '{end_date}'")
        if platform:
            conditions.append(f"platform = '{platform}'")

        where_clause = " AND ".join(conditions) if conditions else None

        return self.get_table_data(
            "fees",
            where=where_clause,
            order_by="date_time"
        )

    def get_refunds(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        platform: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch refund data from BigQuery.

        Args:
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            platform: Filter by platform (Amazon, Shopify, etc.)

        Returns:
            DataFrame with refund transactions
        """
        conditions = []

        if start_date:
            conditions.append(f"DATE(date_time) >= '{start_date}'")
        if end_date:
            conditions.append(f"DATE(date_time) <= '{end_date}'")
        if platform:
            conditions.append(f"platform = '{platform}'")

        where_clause = " AND ".join(conditions) if conditions else None

        return self.get_table_data(
            "refunds",
            where=where_clause,
            order_by="date_time"
        )

    def get_forecast(
        self,
        start_month: Optional[str] = None,
        end_month: Optional[str] = None,
        platform: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch forecast data from BigQuery.

        Args:
            start_month: Start month filter (YYYY-MM-DD)
            end_month: End month filter (YYYY-MM-DD)
            platform: Filter by platform

        Returns:
            DataFrame with SKU-level forecasts
        """
        conditions = []

        if start_month:
            conditions.append(f"DATE(month) >= '{start_month}'")
        if end_month:
            conditions.append(f"DATE(month) <= '{end_month}'")
        if platform:
            conditions.append(f"platform = '{platform}'")

        where_clause = " AND ".join(conditions) if conditions else None

        return self.get_table_data(
            "forecast",
            where=where_clause,
            order_by="month, sku"
        )

    def get_vendors(self) -> pd.DataFrame:
        """
        Fetch vendor master data with payment terms.

        Returns:
            DataFrame with vendor information
        """
        return self.get_table_data(
            "vendors",
            order_by="Name"
        )

    def get_purchase_orders(
        self,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch purchase order data with line items.

        Args:
            status: Filter by status (Open, Closed, etc.)
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)

        Returns:
            DataFrame with PO line items
        """
        conditions = []

        if status:
            conditions.append(f"status = '{status}'")
        if start_date:
            conditions.append(f"order_date >= '{start_date}'")
        if end_date:
            conditions.append(f"order_date <= '{end_date}'")

        where_clause = " AND ".join(conditions) if conditions else None

        return self.get_table_data(
            "po_line_item",
            where=where_clause,
            order_by="order_date"
        )

    def get_invoices(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        vendor: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch vendor invoice data.

        Args:
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            vendor: Filter by vendor name

        Returns:
            DataFrame with invoice data
        """
        conditions = []

        if start_date:
            conditions.append(f"invoice_date >= '{start_date}'")
        if end_date:
            conditions.append(f"invoice_date <= '{end_date}'")
        if vendor:
            conditions.append(f"vendor = '{vendor}'")

        where_clause = " AND ".join(conditions) if conditions else None

        return self.get_table_data(
            "invoices",
            where=where_clause,
            order_by="invoice_date"
        )

    def get_items(self) -> pd.DataFrame:
        """
        Fetch SKU master data with pricing and costs.

        Returns:
            DataFrame with item/SKU data
        """
        return self.get_table_data("item")

    def query_from_file(self, sql_file_path: Path) -> pd.DataFrame:
        """
        Execute a SQL query from a .sql file.

        Args:
            sql_file_path: Path to SQL file

        Returns:
            pandas DataFrame with query results

        Example:
            >>> bq = BigQueryConnector()
            >>> df = bq.query_from_file(Path("src/queries/revenue.sql"))
        """
        with open(sql_file_path, 'r') as f:
            sql = f.read()

        # Replace dataset placeholders if present
        sql = sql.replace("{project_id}", self.project_id)
        sql = sql.replace("{dataset}", self.dataset)

        return self.query(sql)

    def test_connection(self) -> bool:
        """
        Test BigQuery connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            df = self.query("SELECT 1 as test")
            return len(df) == 1 and df.iloc[0]['test'] == 1
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False

    def get_available_tables(self) -> List[str]:
        """
        List all available tables in the dataset.

        Returns:
            List of table names
        """
        tables = self.client.list_tables(f"{self.project_id}.{self.dataset}")
        return [table.table_id for table in tables]

    def get_table_schema(self, table_name: str) -> List[Dict[str, str]]:
        """
        Get schema information for a table.

        Args:
            table_name: Name of the table

        Returns:
            List of dicts with column name and data type

        Example:
            >>> bq = BigQueryConnector()
            >>> schema = bq.get_table_schema("deposits")
            >>> # [{'name': 'platform', 'type': 'STRING'}, ...]
        """
        table_ref = f"{self.project_id}.{self.dataset}.{table_name}"
        table = self.client.get_table(table_ref)

        return [
            {"name": field.name, "type": field.field_type, "mode": field.mode}
            for field in table.schema
        ]
