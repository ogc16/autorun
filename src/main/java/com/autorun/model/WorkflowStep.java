package com.autorun.model;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
public class WorkflowStep {
    private Long scriptId;
    private String name;
    private String paramsJson;
    private String condition;
    private WorkflowStepOnError onError = WorkflowStepOnError.STOP;
    private int timeoutSeconds = 600;
    private int order;
}
