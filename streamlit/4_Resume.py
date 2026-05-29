# ruff: noqa: F401
from pathlib import Path
import re
from textwrap import dedent

import streamlit as st

from job_search.config import P_PROCESSED, P_RAW
import utils as ut

P_resume_md = P_RAW / 'AW_Resume.md'
P_resume = P_PROCESSED / 'AW_Resume.pdf'
resume_md = ut.load_md(P_resume_md)

with st.expander("AW_Resume"):
    # if st.button("Clean markdown"):
    #     resume_md = re.sub("<!-- .* -->", "", resume_md)
    tab1, tab2, tab3 = st.tabs(['Text', 'Markdown', 'PDF'])
    with tab1:
        # st.text(resume_md)
        st.code(resume_md, language='md', wrap_lines=True)
    with tab2:
        resume_md_stripped = re.sub("<!-- .* -->", "", resume_md)
        st.markdown(resume_md_stripped)
    with tab3:
        st.pdf(P_resume, height=900)
        # st.pdf(P_resume, height="stretch")

md_lines = resume_md
with st.expander("Copy Paste"):
    "#### Protein Design Technology"
    # "February 2026 – Present"
    # "Emeryville, CA"
    # "Consultant (AI Engineer)"
    ut.md(dedent("""
        As part of a startup, leveraged proprietary and public datasets to develop predictive AI model for drug discovery.

        - Integrated antibody sequences from SAbDab (public dataset), phage display, and FACS (flow cytometry) data to create training and evaluation set for AI model
        - Built a reproducible end-to-end ML pipeline in Python, establishing coding standards and Git workflows for maintainability and scalability
        - Researched cutting‑edge antibody–antigen prediction methods; guided leadership on experimental focus and reported progress in weekly executive meetings
    """), False)
    "#### Roche Diagnostics	November 2020 – May 2025 Santa Clara, CA"
    # "Data Scientist"
    ut.md(dedent("""
        Analyzed large-scale healthcare datasets and developed machine learning solutions to support clinical research, product strategy, and diagnostic innovation.

        - Executed a health economics and outcomes research (HEOR) study comparing healthcare resource utilization and total costs of diabetes monitoring devices from large-scale claims data (MarketScan) using propensity score matching, resulting in publication in a peer-reviewed journal (AJMC) and supporting Roche Diabetes Care commercial strategy
        - Developed and deployed ML pipeline with NLP (Named Entity Recognition, Relation Extraction) pipeline to extract clinical facts from unstructured pathology reports, reducing manual entry time by ~50% and enabling longitudinal patient tracking within navify Clinical Hub
        - Conducted epidemiological studies using SEER cancer registry data to discover prevalence and incidence trends, delivering visualized insights for Medical Affairs stakeholders
        - Built an interactive Streamlit dashboard to showcase automated traversal of NCCN clinical guidelines from patient EHR data, facilitating customer interviews that informed future product use-cases
        - Conducted exploratory data analysis (EDA) and feasibility assessments (chart review and TriNetX EHR data) of the IL-6 immunoassay, supporting FDA Q-Sub regulatory submissions in the context of neonatal sepsis diagnosis and COVID patient intubation risk stratification
        - Mentored junior data scientists, reviewed programming deliverables, and contributed to standardization of analytic workflows across the RWD (Real-World Data) and data science teams
        - Contributed to a 6-person data science team to predict mortality and hospital readmission with XGBoost, placing top 10 (out of 300+ global teams) in the 2023 FDA V-CHAMPS heart failure prediction challenge
    """), False)

    "#### Halicioglu Data Science Institute, UC San Diego	April 2019 – July 2020"
    # "Graduate Student Researcher (Navy Contractor)"
    ut.md(dedent("""
        Applied data science research on Navy fleet and crew data to reveal trends and offer improvements to shipboard IT system operations.

        - Investigated factors that impact effectiveness of IT technicians among dozens of Navy ships in a 6 year period, empowering data-driven decision-making
        - Uncovered key analytical insights (ship staffing, crew training, open vs closed IT tickets, etc.) over time per ship by wrangling unstructured data with Pandas and visualizing results using Plotly
        - Leveraged NLP (text preprocessing and topic modeling) for root-cause analysis of over 10K trouble tickets, identifying recurring incidents and suggesting associated resolutions
    """), False)

    "#### HPE Aruba Networking, Santa Clara, CA	June 2018 – September 2018"
    # "Data Science Intern"
    ut.md(dedent("""
        Developed big data pipelines and machine learning prototypes to improve real-time network monitoring and anomaly detection.

        - Prototyped real-time network anomaly detection model for Aruba NetInsight cloud dashboard, improving customer experience in monitoring their internet traffic
        - Interactively visualized model for tuning, debugging, and diagnostics using Bokeh
        - Built a production-ready PySpark backend for processing large-scale network data, improving system efficiency and scalability for cloud-based analytics
    """), False)

    "#### Northrop Grumman, San Diego, CA	June 2017 – September 2017"
    # "Software Engineer Intern"
    ut.md(dedent("""
        Designed and tested software applications to monitor and control aircraft systems within an Agile engineering environment.

        - Developed Java Swing GUI (Graphical User Interface) to monitor and control aircraft hardpoints and test in-flight dynamics, ultimately gaining approval from test pilot end-user
        - Verified correct implementation of Java GUI by using Wireshark to debug network packets sent and received by GUI
        - Engaged in Agile methodology (Jira) and testing (JUnit) to deploy software efficiently and reliably
    """), False)
    # ut.markdown()