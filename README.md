# Rearc Data Quest

![CI/CD Pipeline](https://github.com/seanpavlak/quest/actions/workflows/ci-cd.yml/badge.svg)
![Code Coverage](https://codecov.io/gh/seanpavlak/quest/branch/master/graph/badge.svg?token=)

### Q. What is this quest?
It is a fun way to assess your data skills. It is also a good representative sample of the work we do at Rearc.

### Q. So what skills should I have?
* Data management / data engineering concepts.
* Programming language (python, java, scala, etc).
* AWS knowledge (Lambda, SQS, CloudWatch logs).
* Infrastructure-as-code (Terraform, CloudFormation, etc)

### Q. What do I have to do?
This quest consists of 4 different parts. Putting all 4 parts together we will have a Data Pipeline architecture.
- Part 1 and Part 2 will showcase your skills with data management, AWS concepts, and your overall data engineering skillset.
  The goal is to source data from different places and store it in-house.
- Part 3 will showcase your data analytics skills. The goal is to find some interesting insights with data.
- Lastly, Part 4 will put all the pieces together. The goal here is to showcase your experience with automation and AWS services.

#### Part 1: AWS S3 & Sourcing Datasets
1. Republish [this open dataset](https://download.bls.gov/pub/time.series/pr/) in Amazon S3 and share with us a link.
    - You may run into 403 Forbidden errors as you test accessing this data. There is a way to comply with the BLS data access policies and re-gain access to fetch this data programatically - we have included some hints as to how to do this at the bottom of this README in the Q/A section.
2. Script this process so the files in the S3 bucket are kept in sync with the source when data on the website is updated, added, or deleted.
    - Don't rely on hard coded names - the script should be able to handle added or removed files.
    - Ensure the script doesn't upload the same file more than once.

#### Part 2: APIs
1. Create a script that will fetch data from [this API](https://honolulu-api.datausa.io/tesseract/data.jsonrecords?cube=acs_yg_total_population_1&drilldowns=Year%2CNation&locale=en&measures=Population).
   You can read the documentation [here](https://datausa.io/about/api/).
2. Save the result of this API call as a JSON file in S3.

#### Part 3: Data Analytics
0. Load both the csv file from **Part 1** `pr.data.0.Current` and the json file from **Part 2**
   as dataframes ([Spark](https://spark.apache.org/docs/1.6.1/api/java/org/apache/spark/sql/DataFrame.html),
                  [Pyspark](https://spark.apache.org/docs/latest/api/python/reference/api/pyspark.sql.DataFrame.html),
                  [Pandas](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html),
                  [Koalas](https://koalas.readthedocs.io/en/latest/),
                  etc).

1. Using the dataframe from the population data API (Part 2),
   generate the mean and the standard deviation of the annual US population across the years [2013, 2018] inclusive.

2. Using the dataframe from the time-series (Part 1),
   For every series_id, find the *best year*: the year with the max/largest sum of "value" for all quarters in that year. Generate a report with each series id, the best year for that series, and the summed value for that year.
   For example, if the table had the following values:

    | series_id   | year | period | value |
    |-------------|------|--------|-------|
    | PRS30006011 | 1995 | Q01    | 1     |
    | PRS30006011 | 1995 | Q02    | 2     |
    | PRS30006011 | 1996 | Q01    | 3     |
    | PRS30006011 | 1996 | Q02    | 4     |
    | PRS30006012 | 2000 | Q01    | 0     |
    | PRS30006012 | 2000 | Q02    | 8     |
    | PRS30006012 | 2001 | Q01    | 2     |
    | PRS30006012 | 2001 | Q02    | 3     |

    the report would generate the following table:

    | series_id   | year | value |
    |-------------|------|-------|
    | PRS30006011 | 1996 | 7     |
    | PRS30006012 | 2000 | 8     |

3. Using both dataframes from Part 1 and Part 2, generate a report that will provide the `value`
   for `series_id = PRS30006032` and `period = Q01` and the `population` for that given year (if available in the population dataset).
   The below table shows an example of one row that might appear in the resulting table:

    | series_id   | year | period | value | Population |
    |-------------|------|--------|-------|------------|
    | PRS30006032 | 2018 | Q01    | 1.9   | 327167439  |

    **Hints:** when working with public datasets you sometimes might have to perform some data cleaning first.
   For example, you might find it useful to perform [trimming](https://stackoverflow.com/questions/35540974/remove-blank-space-from-data-frame-column-values-in-spark) of whitespaces before doing any filtering or joins


4. Submit your analysis, your queries, and the outcome of the reports as a [.ipynb](https://fileinfo.com/extension/ipynb) file.

#### Part 4: Infrastructure as Code & Data Pipeline with AWS CDK
0. Using [AWS CloudFormation](https://aws.amazon.com/cloudformation/), [AWS CDK](https://aws.amazon.com/cdk/) or [Terraform](https://www.terraform.io/), create a data pipeline that will automate the steps above.
1. The deployment should include a Lambda function that executes
   Part 1 and Part 2 (you can combine both in 1 lambda function). The lambda function will be scheduled to run daily.
2. The deployment should include an SQS queue that will be populated every time the JSON file is written to S3. (Hint: [S3 - Notifications](https://docs.aws.amazon.com/AmazonS3/latest/userguide/NotificationHowTo.html))
3. For every message on the queue - execute a Lambda function that outputs the reports from Part 3 (just logging the results of the queries would be enough. No .ipynb is required).


### Q. Do I have to do all these?
You can do as many as you like. We suspect though that once you start you won't be able to stop. It's addictive.

### Q. What do I have to submit?

#### ✅ Submission Checklist

All required submission items are completed and documented below:

1. **Link to data in S3 and source code (Part 1)**
   - ✅ **S3 Bucket Link**: [View Data in S3](https://rearc-data-pipeline-data-08041c62.s3.us-east-1.amazonaws.com/)
   - ✅ **Main BLS File**: [pr.data.0.Current](https://rearc-data-pipeline-data-08041c62.s3.us-east-1.amazonaws.com/pr.data.0.Current)
   - ✅ **Source Code**: [`src/rearc/data_sync/bls_sync.py`](src/rearc/data_sync/bls_sync.py) - BLS data sync implementation
   - ✅ **Documentation**: See [Part 1 Implementation](docs/README.md#part-1-bls-data-sync) for details

2. **Source code (Part 2)**
   - ✅ **Source Code**: [`src/rearc/data_sync/population.py`](src/rearc/data_sync/population.py) - Population API fetch implementation
   - ✅ **Population Data Files**: Available in S3 with pattern `population_data_*.json`
   - ✅ **Documentation**: See [Part 2 Implementation](docs/README.md#part-2-population-api-fetch) for details

3. **Source code in .ipynb file format and results (Part 3)**
   - ✅ **Jupyter Notebook**: [`notebooks/data_analysis.ipynb`](notebooks/data_analysis.ipynb)
   - ✅ **Analytics Queries**: [`src/rearc/analytics/queries.py`](src/rearc/analytics/queries.py)
   - ✅ **Test Results**: See [Test Suite Summary](tests/TEST_SUITE_SUMMARY.md) for query results
   - ✅ **Documentation**: See [Part 3 Implementation](docs/README.md#part-3-analytics-queries) for details

4. **Source code of the data pipeline infrastructure (Part 4)**
   - ✅ **Terraform Infrastructure**: [`infrastructure/terraform/`](infrastructure/terraform/) - Complete IaC configuration
   - ✅ **Lambda Functions**: 
     - Data Sync: [`infrastructure/lambda/data_sync/`](infrastructure/lambda/data_sync/)
     - Analytics: [`infrastructure/lambda/analytics/`](infrastructure/lambda/analytics/)
   - ✅ **CI/CD Pipeline**: [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml) - Automated deployment
   - ✅ **Deployment Guide**: [Complete Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
   - ✅ **Architecture**: See [Architecture Overview](docs/DEPLOYMENT_GUIDE.md#architecture-overview)

5. **README or documentation**
   - ✅ **Main README**: This file
   - ✅ **Deployment Guide**: [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) - Comprehensive deployment instructions
   - ✅ **Documentation**: [docs/README.md](docs/README.md) - Implementation details
   - ✅ **Test Documentation**: [tests/README.md](tests/README.md) and [tests/TEST_SUITE_SUMMARY.md](tests/TEST_SUITE_SUMMARY.md)

#### 🚀 Quick Links

- **S3 Data Bucket**: [View Data](https://rearc-data-pipeline-data-08041c62.s3.us-east-1.amazonaws.com/)
- **GitHub Repository**: [seanpavlak/quest](https://github.com/seanpavlak/quest)
- **CI/CD Status**: [GitHub Actions](https://github.com/seanpavlak/quest/actions)
- **Code Coverage**: [Codecov Report](https://codecov.io/gh/seanpavlak/quest)
- **Deployment Guide**: [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)
- **Infrastructure Outputs**: [`config/outputs.json`](config/outputs.json)

#### 📊 Current Infrastructure Status

Infrastructure is automatically deployed via CI/CD on every merge to `master`. The `config/outputs.json` file is automatically updated after each deployment to keep it in sync with the actual AWS resources.

**Current Deployment** (from [`config/outputs.json`](config/outputs.json)):
- **S3 Bucket**: `rearc-data-pipeline-data-08041c62`
  - **URL**: https://rearc-data-pipeline-data-08041c62.s3.us-east-1.amazonaws.com/
- **Data Sync Lambda**: `rearc-data-pipeline-data-sync` (runs daily at 2 AM UTC)
- **Analytics Lambda**: `rearc-data-pipeline-analytics` (triggered by S3 events)
- **SQS Queue**: `rearc-data-pipeline-s3-notifications`
- **CloudWatch Logs**: Available for both Lambda functions

> **Note**: Infrastructure outputs are automatically refreshed:
> - After each CI/CD deployment (on merge to master)
> - Daily via scheduled workflow (at 1 AM UTC)
> - On manual trigger via GitHub Actions
> - To manually refresh outputs, run `./scripts/refresh_outputs.sh`

### Q. How do I share the submission?
Your submission should be emailed back to us as one or both of the following:

1. A link to a public hosted git repository in your own namespace
1. A compressed file containing your project directory (zip, tgz, etc). Include the .git sub-directory if you used git.

### Q. What if I successfully complete all the steps?
We have many more for you to solve as a member of the Rearc team!

### Q. What if I fail?
Do. Or do not. There is no fail.

### Q. Can I share this quest with others?
No.

### Q. How do I get around the 403 error when I try to fetch BLS data?
<details>
<summary>Hint 1</summary>
  The BLS data access policies can be found here: https://www.bls.gov/bls/pss.htm
</details>
<details>
<summary>Hint 2</summary>
  The policy page says:

```BLS also reserves the right to block robots that do not contain information that can be used to contact the owner. Blocking may occur in real time.```

How could you add information to your programmatic access requests to let BLS contact you?
</details>
<details>
<summary>Hint 3</summary>
  Adding a <code>User-Agent</code> header to your request with contact information will comply with the BLS data policies and allow you to keep accessing their data programmatically.
</details>

### Q. Can I use AI to assist me?
You may use AI as a reference tool but there will be a strong expectation to exhibit the same expertise and understanding from your submission in your interview. In addition we encourage you to be open about any usage! Please document what you used, what your prompts were, how it helped, what it got wrong, etc.
