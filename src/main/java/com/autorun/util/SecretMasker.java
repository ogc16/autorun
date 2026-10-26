package com.autorun.util;

import java.util.regex.Pattern;

public final class SecretMasker {
    private static final Pattern TOKEN = Pattern.compile("(?i)(token|api[_-]?key|password|secret|passwd|authorization|bearer)[=:\"\\s]+([^\s,\\\"']+)");
    private static final Pattern AWS_KEY = Pattern.compile("(AKIA[0-9A-Z]{16})");
    private static final Pattern PRIVATE_KEY = Pattern.compile("-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----");
    private static final Pattern GENERIC_LONG = Pattern.compile("([A-Za-z0-9+/]{32,}={0,2})");

    private SecretMasker() {}

    public static String mask(String input) {
        if (input == null || input.isEmpty()) {
            return input;
        }
        String masked = input;
        masked = TOKEN.matcher(masked).replaceAll(m -> m.group(1) + "=***MASKED***");
        masked = AWS_KEY.matcher(masked).replaceAll("***AWS_KEY_MASKED***");
        masked = PRIVATE_KEY.matcher(masked).replaceAll("***PRIVATE_KEY_MASKED***");
        masked = GENERIC_LONG.matcher(masked).replaceAll("***MASKED***");
        return masked;
    }
}
