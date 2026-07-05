Topic: Data Cleaning and Missing Values
Note:
Data cleaning is the process of finding and fixing problems in a dataset before analysis or modeling.

Real-world datasets often contain messy values. Common problems include missing values, duplicate rows, inconsistent labels, incorrect data types, impossible values, and outliers.

Missing values are blank or unavailable entries in a dataset. They can happen because a question was skipped, a sensor failed, a field was not collected, or data from two systems did not match correctly.

Before fixing missing values, analysts should first measure how much data is missing. A common first step is counting missing values in each column and calculating the percentage of missing values.

Missing data can appear in different patterns:
- A few random values are missing.
- A whole column has many missing values.
- One group has more missing values than another group.
- Missingness is related to the thing being measured.

The right response depends on the context. If only a few rows are missing important values, removing those rows may be reasonable. If many values are missing, deleting rows can remove too much information.

Imputation means filling in missing values. For numeric columns, common simple choices include the mean, median, or a fixed value such as zero. The median is often safer than the mean when the data has outliers.

For categorical columns, missing values can sometimes be filled with the most common category. Another option is to create a new category such as "Unknown" or "Not reported."

Analysts should be careful when filling missing values. Imputation can make a dataset look more complete than it really is, and it can change patterns in the data.

Duplicate rows are another common data quality issue. Duplicates can happen when the same record is collected twice or when files are combined incorrectly. Analysts should check whether duplicate rows are true duplicates or separate events that look similar.

Data types should also be checked. Dates should be stored as dates, numbers should be stored as numeric values, and categories should use consistent labels.

Inconsistent labels can split one category into several versions. For example, "NY", "New York", and "new york" may all refer to the same place. Standardizing labels helps avoid misleading counts.

Impossible values should be investigated. Examples include negative ages, percentages above 100, or dates from the future. These values may be data entry errors or special codes that need documentation.

Good data cleaning should be documented. Analysts should record what changes were made, why they were made, and how many rows or values were affected.

The goal of data cleaning is not to make the data perfect. The goal is to make the data reliable enough for the question being asked, while being honest about limitations.
