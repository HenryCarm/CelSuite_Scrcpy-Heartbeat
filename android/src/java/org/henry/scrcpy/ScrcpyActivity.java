package org.henry.scrcpy;

import android.content.Context;
import android.os.Bundle;
import android.util.Log;
import org.kivy.android.PythonActivity;

public class ScrcpyActivity extends PythonActivity {
    private static final String TAG = "ScrcpyActivity";

    @Override
    public Object getSystemService(String name) {
        if (Context.SENSOR_SERVICE.equals(name)) {
            Log.w(TAG, "Blocked SENSOR_SERVICE to prevent Samsung JNI UTF-8 abort");
            return null;
        }
        return super.getSystemService(name);
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        // Do not call super to avoid PythonActivity's sensor lookup NPE
        try {
            if (mSingleton != null) {
                onNativeFocusChanged(hasFocus);
            }
        } catch (Throwable t) {
            Log.w(TAG, "Safe onWindowFocusChanged: " + t.getMessage());
        }
    }

    @Override
    protected void onResume() {
        try {
            super.onResume();
        } catch (Throwable t) {
            Log.w(TAG, "Safe onResume: " + t.getMessage());
        }
        startSDLThreadIfNeeded();
    }

    public static void startSDLThreadIfNeeded() {
        try {
            if (mSDLThread == null) {
                Log.i(TAG, "Starting SDLThread directly from ScrcpyActivity...");
                mSDLThread = new Thread(new SDLMain(), "SDLThread");
                mSDLThread.start();
            }
        } catch (Throwable t) {
            Log.w(TAG, "startSDLThreadIfNeeded: " + t.getMessage());
        }
    }
}
