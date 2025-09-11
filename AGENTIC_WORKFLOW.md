## Agentic Workflow Diagram

This diagram shows how agents, tasks, tools, and report artifacts flow through the sequential CrewAI run defined in `crew.py` with config from `config/agents.yaml` and `config/tasks.yaml`.


```mermaid
flowchart TB
    %% Legend
    classDef agent fill:#eef7ff,stroke:#5aa0ff,stroke-width:1px;
    classDef tool fill:#fff7e6,stroke:#ffb74d,stroke-width:1px;
    classDef file fill:#f5f5f5,stroke:#9e9e9e,stroke-width:1px,stroke-dasharray:3 2;
    classDef action fill:#e8f5e9,stroke:#66bb6a,stroke-width:1px;

    START([Crew start: Process.sequential]) --> T1

    %% Task 1: Stock Screening
    subgraph A1[Task: stock_screen]
      direction TB
      AG1[Agent: stock_screener]:::agent --> TOOL_SS[(StockScreenerTool)]:::tool
      TOOL_SS --> OUT_SR[screen_report.md\nTop 10 BUY candidates]:::file
    end
    T1[Run stock_screen]:::action --> A1 --> T2

    %% Task 2: ETF Analysis
    subgraph A2[Task: etf_analysis]
      direction TB
      AG2[Agent: etf_analyst]:::agent --> TOOL_SR1[(FileReadTool: screen_report.md)]:::tool
      AG2 --> TOOL_SO1[(FileReadTool: stocks_owned.csv)]:::tool
      AG2 --> TOOL_TA1[(TickerAnalyticsLookupTool: JPST, QQQ, SPY, IWM, VIX)]:::tool
      TOOL_TA1 --> OUT_ER[etf_report.md\nFindings for QQQ/JPST/SPY/IWM, Weighting opinion]:::file
    end
    T2[Run etf_analysis]:::action --> A2 --> T3

    %% Task 3: Technical Analysis
    subgraph A3[Task: technical_analysis]
      direction TB
      AG3[Agent: technical_analyst]:::agent --> TOOL_SO2[(FileReadTool: stocks_owned.csv)]:::tool
      AG3 --> TOOL_SR2[(FileReadTool: screen_report.md)]:::tool
      AG3 --> TOOL_TA2[(TickerAnalyticsLookupTool: RSI/MACD/SMA, News)]:::tool
      TOOL_TA2 --> OUT_TR[technical_report.md\nSELL/BUY candidates, Rationale]:::file
    end
    T3[Run technical_analysis]:::action --> A3 --> T4

    %% Task 4: Fundamental Analysis
    subgraph A4[Task: fundamental_analysis]
      direction TB
      AG4[Agent: fundamental_analyst]:::agent --> TOOL_SO3[(FileReadTool: stocks_owned.csv)]:::tool
      AG4 --> TOOL_SR3[(FileReadTool: screen_report.md)]:::tool
      AG4 --> TOOL_TA3[(TickerAnalyticsLookupTool: Fundamentals, News)]:::tool
      TOOL_TA3 --> OUT_FR[fundamental_report.md\nSELL/BUY candidates, Rationale]:::file
    end
    T4[Run fundamental_analysis]:::action --> A4 --> T5

    %% Task 5: Portfolio Adjustments
    subgraph A5[Task: portfolio_adjustments]
      direction TB
      AG5[Agent: portfolio_manager]:::agent --> TOOL_SO4[(FileReadTool: stocks_owned.csv)]:::tool
      AG5 --> TOOL_AD[(FileReadTool: account_details.csv)]:::tool
      AG5 --> TOOL_TR[(FileReadTool: technical_report.md)]:::tool
      AG5 --> TOOL_FR[(FileReadTool: fundamental_report.md)]:::tool
      AG5 --> TOOL_TA4[(TickerAnalyticsLookupTool)]:::tool
      TOOL_TR --> AG5
      TOOL_FR --> AG5
      AG5 --> OUT_PR[portfolio_report.md\n% by company, sector, BUY/SELL adjustments]:::file
    end
    T5[Run portfolio_adjustments]:::action --> A5 --> T6

    %% Task 6: Final Report
    subgraph A6[Task: final_report]
      direction TB
      AG6[Agent: report_analyst]:::agent --> TOOL_SR4[(FileReadTool: screen_report.md)]:::tool
      AG6 --> TOOL_TR2[(FileReadTool: technical_report.md)]:::tool
      AG6 --> TOOL_FR2[(FileReadTool: fundamental_report.md)]:::tool
      AG6 --> TOOL_PR[(FileReadTool: portfolio_report.md)]:::tool
      TOOL_SR4 --> AG6
      TOOL_TR2 --> AG6
      TOOL_FR2 --> AG6
      TOOL_PR --> AG6
      AG6 --> OUT_FRPT[final_report.md\nBUY/SELL sections, rationale, % by company/sector, adjustments]:::file
    end
    T6[Run final_report]:::action --> A6 --> T7

    %% Task 7: Archive Report with retry
    subgraph A7[Task: archive_report]
      direction TB
      AG7[Agent: report_analyst]:::agent --> TOOL_AR[(ReportArchiveTool: Elasticsearch)]:::tool
      OUT_FRPT --> AG7
  AG7 --> D1["Archive succeeded?"]
  D1 -->|Yes| OUT_AR[Archive response]:::file
  D1 -->|No| R1(Wait 30s and retry up to 3x):::action
  R1 --> AG7
    end
    T7[Run archive_report]:::action --> A7 --> END([Crew complete])

    %% Notes
    %% Report paths are read via FileReadTool using LOCAL_DATA_DIR
```

Notes:
- Execution is sequential in the order defined in `crew.py` (stock_screen → etf_analysis → technical_analysis → fundamental_analysis → portfolio_adjustments → final_report → archive_report).
- FileReadTool instances for reports and CSVs resolve paths using the `LOCAL_DATA_DIR` environment variable from `.env`.
- The archive step retries up to 3 times with a 30-second delay if the first attempt fails.
