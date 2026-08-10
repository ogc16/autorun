package com.autorun.util;

import com.autorun.model.ScriptParam;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.List;
import java.util.Map;

public final class JsonUtil {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private JsonUtil() {
    }

    public static String toJson(Object value) {
        try {
            return MAPPER.writeValueAsString(value);
        } catch (Exception e) {
            return "{}";
        }
    }

    public static Map<String, String> parseArguments(String json) {
        if (json == null || json.isBlank()) {
            return Map.of();
        }
        try {
            return MAPPER.readValue(json, new TypeReference<Map<String, String>>() {
            });
        } catch (Exception e) {
            return Map.of();
        }
    }

    public static List<ScriptParam> parseParams(String json) {
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            return MAPPER.readValue(json, new TypeReference<List<ScriptParam>>() {
            });
        } catch (Exception e) {
            return List.of();
        }
    }

    public static String serializeParams(List<ScriptParam> params) {
        if (params == null) {
            return null;
        }
        return toJson(params);
    }
}
