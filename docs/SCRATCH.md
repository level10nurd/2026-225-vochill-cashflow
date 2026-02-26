## 1
1. Accounting Data (Most Critical)                                     
                                                                         
  Do you have any of these available to upload?                         
  - QuickBooks or Xero export (past 3-6 months of transactions)?
    - yes, quickbooks   
  - Bank statements from Frost Bank (CSV)? 
    - yes                              
  - Credit card statements (Amex, Chase, Southwest)?  
    - yes                   
  - Chart of accounts list?           
    - see `data/coa.csv`                                   
                                                                         
  2. Ecommerce Platform Data
  **note**: all dataa from reports provided are also fed into bigquery                                             
                                                                         
  - Amazon Seller Central payout reports?
    -  `examples/amazon_transaction_report_example.txt`                              
  - Shopify payout/transaction history?
    - `examples/shopify_payout_report_example.csv`                                
  - What are the typical payout schedules? (e.g., Amazon every 2 weeks,  
  Shopify daily?) 
    - shopify: every weekday
    - amazon: every 2 weeks                                                       
                                                                         
  3. Known Commitments                                                   
                                                                         
  - Frost Bank LOC terms (limit, interest rate, current balance)? 
    - see `docs/SBA Promissory Note Vochill.pdf`        
  - Any fixed monthly obligations (rent, payroll, subscriptions)? 
    - yes. 
    - lets identify and add when we bring in accounting data       
  - Planned capital expenditures?
    - yes. 
    - lets buildout a data structure for this when building out, and i can add.                                         
  - Inventory purchase commitments?
    - not yet, but there will be very soon!                                     
                                                                         
  4. Current Cash Position                                               
                                                                         
  - Starting cash balance across all accounts?
    - get from accounting data                           
  - Current LOC drawn amount?     
    - get from accounting data

# 2
Im thinking that we should identify new tables that need to be added to bigquery. 
- bigquery has lots of tables relating to sales, marketing, and operations, but not really many for financial/cashflow
- as part of our cashflow build, we should identify what dataschema our work needs and add to our bigquery datamodel

# QuestionsComments
- loans
  - we have more than just the SBA loan. We have equipment loans, balloon loans, and other unsecured debt
  - need functionality to add more
- what does `uv run python scripts/etl_invoices_to_cash.py` do?
  - where is payment data coming from?
  - is it actual payments? or is it calcualted based on due date?
- what additional accounting/finance data do we need to add?
  - provide checklist so i can pull data together
- you mentioned current cashflow shows eekly Expenses: $105,137/week. how can you possibly know that? we haven't uploaded data. where is this coming from?
- what is the best way to automate/integrate the flow of this data from bill.com and quickbooks online into bigquery
