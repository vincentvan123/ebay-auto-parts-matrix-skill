# Sales data sources

MVP uses public U.S. annual sales tables from GoodCarBadCar. Source URLs are explicit in `config/sales_sources.csv` and each cached row stores the URL and refresh date.

Some public pages report a vehicle family rather than individual trims. Attach those rows to the configured family once and do not duplicate the same series across family members.

Source extraction supports current annual HTML tables and legacy embedded chart data. A page with no extractable annual series produces a fetch error; it does not produce zero sales.
