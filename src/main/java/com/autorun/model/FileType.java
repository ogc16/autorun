package com.autorun.model;

public enum FileType {
    PY, SH, PS1, BAT, CMD;

    public static FileType fromFilename(String filename) {
        String ext = "";
        int dot = filename.lastIndexOf('.');
        if (dot >= 0) {
            ext = filename.substring(dot + 1).toLowerCase();
        }
        return switch (ext) {
            case "py" -> PY;
            case "sh" -> SH;
            case "ps1" -> PS1;
            case "bat" -> BAT;
            case "cmd" -> CMD;
            default -> throw new IllegalArgumentException(
                    "Unsupported file type '.%s'. Allowed: .py, .sh, .ps1, .bat, .cmd".formatted(ext));
        };
    }

    public String extension() {
        return switch (this) {
            case PY -> "py";
            case SH -> "sh";
            case PS1 -> "ps1";
            case BAT -> "bat";
            case CMD -> "cmd";
        };
    }
}
