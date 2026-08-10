package com.autorun.util;

import com.autorun.model.ScriptParam;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class ArgumentResolver {

    private ArgumentResolver() {
    }

    /**
     * Resolves positional CLI arguments for a script from the declared parameters
     * and the raw values supplied by the caller. Missing required parameters throw
     * an IllegalArgumentException; missing optional ones fall back to defaults.
     */
    public static List<String> resolveArguments(List<ScriptParam> params,
                                                Map<String, String> values,
                                                List<String> rawArgs) {
        List<String> positional = new ArrayList<>();
        if (params != null) {
            for (ScriptParam p : params) {
                String v = values == null ? null : values.get(p.getName());
                if (v == null || v.isBlank()) {
                    v = p.getDefaultValue();
                }
                if (p.isRequired() && (v == null || v.isBlank())) {
                    throw new IllegalArgumentException(
                            "Missing required parameter '%s'".formatted(p.getName()));
                }
                if (v != null) {
                    positional.add(v);
                }
            }
        }
        if (rawArgs != null) {
            positional.addAll(rawArgs);
        }
        return positional;
    }

    public static Map<String, String> nonBlankValues(Map<String, String> values) {
        Map<String, String> cleaned = new LinkedHashMap<>();
        if (values != null) {
            values.forEach((k, v) -> {
                if (v != null && !v.isBlank()) {
                    cleaned.put(k, v);
                }
            });
        }
        return cleaned;
    }
}
