# Debug a Failure in Vision Analysis Pro

待排查的问题：

{{failure}}

请用“先定位，再修复，再验证”的方式处理。

## Required Steps
1. 先总结症状：报错、异常行为、影响范围
2. 列出最可能相关的文件、配置和测试
3. 给出最短可行复现/验证命令
4. 先提出根因判断，再实施修复
5. 修复后说明如何验证不回归

## Output Format

### Symptom
- ...

### Likely Context
| File | Why relevant |
|------|--------------|

### Hypothesis
- ...

### Fix Plan
1. ...

### Validation
- command

## Constraints
- 不要一上来重构；优先做最小充分修复
- 不要隐藏错误或吞异常
- 如果信息不足，明确指出缺失上下文，而不是猜测实现
