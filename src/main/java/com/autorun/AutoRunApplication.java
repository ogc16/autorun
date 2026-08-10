package com.autorun;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class AutoRunApplication {

    public static void main(String[] args) {
        SpringApplication.run(AutoRunApplication.class, args);
    }
}
