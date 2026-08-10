package com.autorun.model;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
public class ScriptParam {

    private String name;
    private String label;
    private String description;
    private boolean required;
    private String defaultValue;

    public ScriptParam(String name, String label, String description, boolean required, String defaultValue) {
        this.name = name;
        this.label = label;
        this.description = description;
        this.required = required;
        this.defaultValue = defaultValue;
    }
}
