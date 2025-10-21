# Test Diagrams

```mermaid
flowchart LR
  A[Start] --> B{Choice}
  B -- Yes --> C[Go]
  B -- No  --> D[Stop]
```


![test_diagrams diagram](test_diagrams_images/test_diagrams-mermaid-1-75d5d9cfd2.png)
<!-- mmd-rendered:test_diagrams-mermaid-1-75d5d9cfd2.png -->
```mermaid
sequenceDiagram
  participant A
  participant B
  A->>B: Hello
  B-->>A: Hi
```


![test_diagrams diagram](test_diagrams_images/test_diagrams-mermaid-2-cd27d6eced.png)
<!-- mmd-rendered:test_diagrams-mermaid-2-cd27d6eced.png -->
```mermaid
erDiagram
  USER ||--o{ ORDER : places
  ORDER ||--|{ LINE_ITEM : contains
  USER {
    string id
    string name
  }
```

![test_diagrams diagram](test_diagrams_images/test_diagrams-mermaid-3-db5f0ed1ad.png)
<!-- mmd-rendered:test_diagrams-mermaid-3-db5f0ed1ad.png -->
