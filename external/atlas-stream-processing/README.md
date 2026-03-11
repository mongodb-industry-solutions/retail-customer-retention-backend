# ⚡  MongoDB Atlas Stream Processing Setup for Retail Retention Demo

This guide describes how to configure the **MongoDB Atlas Stream Processing** environment used in the Retail Customer Retention demo.  
The setup includes creating a Stream Processing workspace and registering the Atlas database connection used by the processors.

---

## 1. Create a Stream Processing Workspace

In **MongoDB Atlas**:

`Streaming Data → Stream Processing → Create Workspace`

### Recommended Settings

| Setting | Value | Reason |
|------|------|------|
| **Workspace Name** | `retail-retention-demo` | Clear ownership and purpose; easy to identify later. |
| **Tier** | `SP10` | Sufficient for demo-scale pipelines (~2k sessions) while keeping costs low. |
| **Provider / Region** | `AWS / us-east-1 (N. Virginia)` | Should match your Atlas cluster region to reduce latency and avoid cross-region traffic. |
| **Maximum Tier Size (optional)** | Leave default or set to `SP30` | Allows quick scale-up if needed without enabling autoscaling. |

---

## 2. Register the Atlas Database Connection (Connection Registry)

Navigate to your **Stream Processing workspace**:

`Workspace → Connection Registry → Add Connection`

### Connection Configuration

| Setting | Value |
|------|------|
| **Connection Type** | `Atlas Database` |
| **Connection Name** | `retail_customer_retention` |
| **Atlas Cluster** | Select the cluster containing the `leafy_popup_store` database |
| **Execute As** | `Read and write to any database` |

### Why These Permissions?

The stream processor must:

- **Read from:** `events_ingest`
- **Write to:** `session_state`

Granting **read and write access to any database** keeps the configuration simple and is the standard permission model for demos.

---

## 3. Create the Stream Processors (ASPs)

You need to create **4 Atlas Stream Processors** in your workspace. Follow the detailed steps below for the first processor, then replicate the same process for the remaining three.

### Create ASP 1: Session State Builder

1. Navigate to your **Stream Processing workspace**
2. Click **Create Processor**
3. Enter the processor name: `asp1_session_state_builder`
4. Open the [asp1_session_state_builder_.js](./asp1_session_state_builder_.js) file from this repository
5. Copy the entire pipeline definition from the file
6. Paste the pipeline into the **Processor Definition editor** in Atlas
7. Click **Create Processor**
8. Click **Start** to begin processing

### Create the Remaining ASPs

Replicate the same steps above for the following three processors:

| Processor Name | Source File |
|----------------|-------------|
| `asp2_exit_risk` | [asp2_exit_risk.js](./asp2_exit_risk.js) |
| `asp2_high_intent` | [asp2_high_intent.js](./asp2_high_intent.js) |
| `asp2_search_friction` | [asp2_search_friction.js](./asp2_search_friction.js) |

### Important

This connection will be reused by the stream processor as both:

- **Source** (reading incoming events)
- **Sink** (writing session state updates)

---