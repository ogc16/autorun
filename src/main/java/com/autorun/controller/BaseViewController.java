package com.autorun.controller;

import com.autorun.model.User;
import com.autorun.security.AppUserDetails;
import com.autorun.service.UserService;
import org.springframework.security.core.Authentication;

public abstract class BaseViewController {

    private final UserService userService;

    protected BaseViewController(UserService userService) {
        this.userService = userService;
    }

    protected User currentUser(Authentication authentication) {
        AppUserDetails principal = (AppUserDetails) authentication.getPrincipal();
        return userService.get(principal.getId());
    }
}
