package org.henry.scrcpy;

import android.content.Context;
import android.util.Log;
import org.kivy.android.PythonActivity;

public class ScrcpyActivity extends PythonActivity {
    private static final String TAG = "ScrcpyActivity";

    @Override
    public Object getSystemService(String name) {
        if (Context.SENSOR_SERVICE.equals(name)) {
            Log.w(TAG, "Blocked SENSOR_SERVICE on Samsung device to prevent JNI Modified UTF-8 crash");
            return null;
        }
        return super.getSystemService(name);
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        try {
            super.onWindowFocusChanged(hasFocus);
        } catch (Exception e) {
            Log.w(TAG, "Safely caught exception in onWindowFocusChanged: " + e.getMessage());
        }
    }

    @Override
    protected void onResume() {
        try {
            super.onResume();
        } catch (Exception e) {
            Log.w(TAG, "Safely caught exception in onResume: " + e.getMessage());
        }
    }

    @Override
    protected void onPause() {
        try {
            super.onPause();
        } catch (Exception e) {
            Log.w(TAG, "Safely caught exception in onPause: " + e.getMessage());
        }
    }

    @Override
    protected void onStop() {
        try {
            super.onStop();
        } catch (Exception e) {
            Log.w(TAG, "Safely caught exception in onStop: " + e.getMessage());
        }
    }

    @Override
    protected void onDestroy() {
        try {
            super.onDestroy();
        } catch (Exception e) {
            Log.w(TAG, "Safely caught exception in onDestroy: " + e.getMessage());
        }
    }
}
