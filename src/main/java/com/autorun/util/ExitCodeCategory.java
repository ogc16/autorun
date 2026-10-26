package com.autorun.util;

public enum ExitCodeCategory {
    SUCCESS(0, "SUCCESS", "Execution completed successfully"),
    GENERIC_FAILURE(1, "GENERIC_FAILURE", "General failure"),
    MISUSE_SHELL(2, "MISUSE_SHELL", "Misuse of shell builtins"),
    COMMAND_NOT_EXECUTABLE(126, "COMMAND_NOT_EXECUTABLE", "Command found but not executable"),
    COMMAND_NOT_FOUND(127, "COMMAND_NOT_FOUND", "Command not found"),
    INVALID_EXIT_ARG(128, "INVALID_EXIT_ARG", "Invalid argument to exit"),
    FATAL_SIGNAL_OFFSET(128, "FATAL_SIGNAL", "Fatal error signal"),
    TIMEOUT(-1, "TIMEOUT", "Execution timed out"),
    CANCELLED(-2, "CANCELLED", "Execution cancelled by user");

    private final int code;
    private final String name;
    private final String description;

    ExitCodeCategory(int code, String name, String description) {
        this.code = code;
        this.name = name;
        this.description = description;
    }

    public int getCode() {
        return code;
    }

    public String getName() {
        return name;
    }

    public String getDescription() {
        return description;
    }

    public static ExitCodeCategory from(int exitCode) {
        if (exitCode == 0) return SUCCESS;
        if (exitCode == 1) return GENERIC_FAILURE;
        if (exitCode == 2) return MISUSE_SHELL;
        if (exitCode == 126) return COMMAND_NOT_EXECUTABLE;
        if (exitCode == 127) return COMMAND_NOT_FOUND;
        if (exitCode == 128) return INVALID_EXIT_ARG;
        if (exitCode > 128 && exitCode < 165) {
            return FATAL_SIGNAL_OFFSET;
        }
        return GENERIC_FAILURE;
    }
}
