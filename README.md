# 议题优先级分析

这个 Python 项目整理与“议题优先级分析”有关的来源观察，帮助传播团队负责人
讨论每月的研究与内容资源安排：查看每个候选议题有哪些信号支撑、各自覆盖到
哪里，比较不同决策取舍对排序的影响，并把月度决定留档备查。

分析输出仅用于讨论资源安排，不构成因果结论，也不代表唯一正确的顺序。

## 工作流程

1. **查看议题档案**——每个候选议题有哪些信号支撑、各自覆盖哪些来源与地区：

   `python -m signal_lab dossier fixtures/candidate_topics.json`

2. **比较口径**——不同权重取舍下排序如何变化；支撑不足的议题列为“待补信息”，
   而不是被当作低优先级：

   ```
   python -m signal_lab compare fixtures/candidate_topics.json \
     --weights '均衡:reporting=1,regional-coverage=1,audience-questions=1' \
     --weights '重视受众:audience-questions=2,reporting=1,regional-coverage=1'
   ```

3. **留档月度决定**——保存当时的数据快照（含哈希）、口径与选择理由；
   档案只增不改：

   ```
   python -m signal_lab decide fixtures/candidate_topics.json \
     --ledger decisions --decision-id 2026-11 --period 2026-11 \
     --select international-cooperation,climate-adaptation \
     --rationale '……' --weights 'reporting=1,regional-coverage=1,audience-questions=1'
   ```

4. **数据补录或修正之后**——待决策名单可以重算（不改写已留档决定），
   并解释名次变化来自真实信号还是覆盖补齐：

   ```
   python -m signal_lab pending 新数据.json --ledger decisions
   python -m signal_lab explain 旧数据.json 新数据.json \
     --weights 'reporting=1,regional-coverage=1,audience-questions=1'
   ```

5. **核验留档**——确认已留档决定的数据与口径未被改动：

   `python -m signal_lab verify --ledger decisions`

安装为可编辑包后也可直接使用 `signal-lab` 命令。

## 开发

需要 Python 3.11 或更高版本。安装开发依赖：`python -m pip install -e .`。

运行测试：`python -m unittest discover -s tests -v`。
构建发行包：`python -m build`。
