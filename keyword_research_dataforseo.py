name: DataForSEO Keyword Research

on:
  workflow_dispatch:
    inputs:
      seed_keywords:
        description: "Comma-separated seed keywords (max 20)"
        required: true
        default: "ac repair dubai,ac not cooling,ac service dubai,air conditioner repair"
      location_name:
        description: "Location name (e.g. 'Dubai,United Arab Emirates' or 'United Arab Emirates')"
        required: false
        default: "United Arab Emirates"
      language_code:
        description: "Language code (e.g. en)"
        required: false
        default: "en"

jobs:
  fetch-keywords:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Run keyword research (DataForSEO)
        env:
          DATAFORSEO_LOGIN: ${{ secrets.DATAFORSEO_LOGIN }}
          DATAFORSEO_PASSWORD: ${{ secrets.DATAFORSEO_PASSWORD }}
          SEED_KEYWORDS: ${{ github.event.inputs.seed_keywords }}
          LOCATION_NAME: ${{ github.event.inputs.location_name }}
          LANGUAGE_CODE: ${{ github.event.inputs.language_code }}
        run: python keyword_research_dataforseo.py

      - uses: actions/upload-artifact@v4
        with:
          name: keyword-data-dataforseo
          path: keyword_data_output.txt
