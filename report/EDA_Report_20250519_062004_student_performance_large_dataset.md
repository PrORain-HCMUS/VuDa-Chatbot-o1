
## 📘 Introduction
The dataset contains information on 10,000 students with various attributes such as age, gender, study hours per week, online courses completed, exam scores, and final grades. It consists of both numerical and categorical data.

## 🧼 Data Quality
There are no missing values or duplicates in the dataset. The column quality seems good with a mix of numerical and categorical variables.

## 🔍 Univariate Analysis
- Age distribution of students

```python
sns.histplot(df['Age'], bins=30, kde=True)
```

_The age distribution is fairly symmetric with most students falling between 20-27 years old._

- Distribution of study hours per week

```python
sns.histplot(df['Study_Hours_per_Week'], bins=30, kde=True)
```

_The study hours per week are right-skewed, indicating that a majority of students study fewer hours._

- Gender distribution

```python
sns.countplot(df['Gender'])
```

_There are slightly more female students in the dataset compared to male students._

- Distribution of exam scores

```python
sns.histplot(df['Exam_Score (%)'], bins=30, kde=True)
```

_The exam scores are normally distributed with a mean around 70%._



## 📊 Correlation Insights
Correlation analysis helps to understand relationships between numerical variables. We expect study hours per week to correlate positively with exam scores and final grades. It would be interesting to explore if stress levels or time spent on social media have any impact on academic performance.

```python
sns.heatmap(df.corr(), annot=True, cmap='coolwarm')
```

_The strongest positive correlation is between study hours per week and exam scores. Surprisingly, there is a negative correlation between time spent on social media and exam scores. Final grades seem to be positively correlated with study hours and exam scores. Self-reported stress levels show weak correlations with academic performance._

## 💡 Final Insights & Recommendations
Based on the exploratory data analysis (EDA) conducted on the dataset containing information on 10,000 students, several interesting patterns and relationships have emerged. The age distribution of students is fairly symmetric, with a majority falling between 20-27 years old. However, the study hours per week are right-skewed, indicating that most students study fewer hours. Additionally, there are slightly more female students in the dataset compared to male students. The exam scores follow a normal distribution with a mean around 70%.

One of the most significant insights from the correlation analysis is the strong positive correlation between study hours per week and exam scores. Surprisingly, there is a negative correlation between time spent on social media and exam scores. Furthermore, final grades show positive correlations with study hours and exam scores. Self-reported stress levels exhibit weak correlations with academic performance.

An unexpected finding is the negative correlation between time spent on social media and exam scores, suggesting that excessive social media use may have a detrimental impact on academic performance. To improve academic outcomes, students should focus on increasing study hours and reducing time spent on social media. Additionally, managing stress levels effectively may also lead to better academic performance.

Recommendations:
- Encourage students to allocate more time to studying each week.
- Educate students on the potential negative effects of excessive social media use on academic performance.
- Provide resources and support for stress management techniques to help students improve their academic outcomes.
