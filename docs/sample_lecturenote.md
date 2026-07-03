Topic: Exploratory Data Analysis and Visualization
Note:
Exploratory Data Analysis, or EDA, is the process of inspecting and summarizing a dataset before building models or making conclusions.

EDA helps us understand:
- what variables are in the dataset
- what each variable means
- whether values are missing
- whether there are outliers
- how variables are distributed
- how variables relate to each other

Common first steps in EDA include checking the shape of the dataset, looking at column names and data types, viewing the first few rows, and calculating summary statistics.

For numeric variables, useful summaries include mean, median, minimum, maximum, standard deviation, and quartiles. Histograms and box plots help show the distribution and reveal skew or outliers.

For categorical variables, useful summaries include counts, percentages, and the number of unique categories. Bar charts are often used to compare category frequencies.

Missing data should be identified early. We can count missing values by column and decide whether to remove rows, fill missing values, or investigate why the data is missing.

Outliers are unusually high or low values. They may be real observations, data entry errors, or special cases. Box plots and scatter plots are common tools for spotting outliers.

Visualization helps communicate patterns that are hard to see in tables. A good visualization should match the data type and the question being asked.

Common chart choices:
- Histogram: distribution of one numeric variable
- Box plot: spread, median, quartiles, and outliers
- Bar chart: counts or comparisons across categories
- Scatter plot: relationship between two numeric variables
- Line chart: trend over time
- Heatmap: patterns in a table or correlation matrix

Correlation measures the strength and direction of a relationship between two numeric variables. A positive correlation means variables tend to increase together. A negative correlation means one tends to decrease as the other increases. Correlation does not prove causation.

Good EDA is iterative. Analysts move between questions, summaries, visualizations, and follow-up checks. The goal is not to prove a final answer immediately, but to understand the data well enough to ask better questions.