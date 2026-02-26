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