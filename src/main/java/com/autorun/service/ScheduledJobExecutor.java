package com.autorun.service;

import com.autorun.config.ResourceNotFoundException;
import com.autorun.model.ScriptJob;
import org.quartz.JobDataMap;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.quartz.QuartzJobBean;

/**
 * Quartz job bean. Spring Boot wires this bean's dependencies (the scheduler
 * factory uses an autowire-capable job factory), so ExecutionService is available
 * even though Quartz instantiates the class reflectively.
 */
public class ScheduledJobExecutor extends QuartzJobBean {

    private ExecutionService executionService;

    @Autowired
    public void setExecutionService(ExecutionService executionService) {
        this.executionService = executionService;
    }

    @Override
    protected void executeInternal(JobExecutionContext context) throws JobExecutionException {
        JobDataMap data = context.getJobDetail().getJobDataMap();
        Long jobId = data.getLong("jobId");
        if (executionService == null) {
            throw new JobExecutionException("ExecutionService not wired");
        }
        executionService.runScheduledJob(jobId);
    }
}
