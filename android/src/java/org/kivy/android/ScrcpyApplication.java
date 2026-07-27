package org.kivy.android;

import android.app.Application;
import android.content.Context;
import android.content.ContextWrapper;

public class ScrcpyApplication extends Application {
    @Override
    protected void attachBaseContext(Context base) {
        // Wrap the base context to block SENSOR_SERVICE access
        // Samsung A035F sensor HAL returns garbage UTF-8 causing JNI abort in SystemSensorManager
        super.attachBaseContext(new ContextWrapper(base) {
            @Override
            public Object getSystemService(String name) {
                if (Context.SENSOR_SERVICE.equals(name)) {
                    // Block sensor service to prevent SystemSensorManager crash on Samsung devices
                    return null;
                }
                return super.getSystemService(name);
            }
        });
    }
}