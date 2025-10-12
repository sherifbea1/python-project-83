### Hexlet tests and linter status:
[![Actions Status](https://github.com/sherifbea1/python-project-83/actions/workflows/hexlet-check.yml/badge.svg)](https://github.com/sherifbea1/python-project-83/actions)

Deploy: https://python-project-83-hjbe.onrender.com

# Page Analyzer
****

## Project Description

Page Analyzer is a website that analyzes specified pages for SEO readiness, similar to PageSpeed Insights.
****


## Installation

### Clone the repository:

```
git clone git@github.com:sherifbea1/python-project-83.git
```

```
cd python-project-83
```

### To use this application, you need to configure the .env file.

After cloning the repository, rename the .env_example file to .env. Inside the file, you will find the SECRET_KEY and
DATABASE_URL variables. Replace their values with your own.
****

### Next, use the command below to install the required dependencies and generate the database tables.

```
make build
```

### Start the application with the following command:

```
make start
```