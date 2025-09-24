# Solid-state synthesis recipe dataset

### For the publication "Text-mined dataset of solid-state syntheses with impurity phases using Large Language Model" by Sanghoon Lee, Kevin Cruse, Viktoriia Baibakova, Gerbrand Ceder, and Anubhav Jain.

[SS_rxns_80806.gz.pkl](SS_rxns_80806.gz.pkl) is the dataset consisting of 80,806 solid-state synthesis recipes.



## 1. Recipe Extraction
LLM outputs were produced using [OpenAI API](https://openai.com/api/) using gpt-4o-2024-05-13 with temperature=0.
[Paperportions_GPT4o_raw_outputs_text_masked.jsonl.gz](Paperportions_GPT4o_raw_outputs_text_masked.jsonl.gz) contains raw GPT4o outputs from 115,795 papers.
```bash
gzip -d Paperportions_GPT4o_raw_outputs_text_masked.jsonl.gz
```

## 2. Post-processing 
```bash
python GPT4o_output_postprocess.py
```
[GPT4o_output_postprocess.py](GPT4o_output_postprocess.py) processes the output string from the LLM to detect reactions from each paper as a Python list of dictionaries.

## 3. How to use the dataset
To start, [example.ipynb](example.ipynb) is a jupyter notebook tutorial on how to load and explore the dataset.



