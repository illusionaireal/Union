# U-012 运行指标口径

- work_count/status_counts：工作记录的当前状态，不是业务验收或真实自治成功率。
- lifecycle_unknown_count：没有宿主生命周期记录；partial表示只观察到升级后发生的变化，既往历史未知。
- dispatch_count：已观察到的派发数，工具续跑也计数；不等于业务尝试次数。
- cycle_seconds：当前delivered工作，从首次启动到最近交付的历时；同工作修订包含在内，不是单次模型耗时。缺任一时间或出现负值即unknown，均值只使用已知样本，并展示已知/未知数量。
- blocked_age：当前blocked状态起点到采集时间；旧工作时间未知则null。读取不回填，也不把unknown/needs_review算作普通blocked。
- U-020真实阶段报告另记预先定义的接受交付/真实尝试、反馈采用、人工介入及实际已知/未知费用。没有尝试时成功率无数据，不填0或100%。
- 资源与费用继续按既有记录；fixture、mock、真实模型和真实业务分别标记。
