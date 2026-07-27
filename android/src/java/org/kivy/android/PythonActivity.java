package org.kivy.android;

import java.io.InputStream;
import java.io.FileWriter;
import java.io.File;
import java.io.IOException;
import java.lang.reflect.InvocationTargetException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Iterator;
import java.util.List;
import java.util.Timer;
import java.util.TimerTask;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.os.AsyncTask;
import android.os.Bundle;
import android.os.PowerManager;
import android.util.Log;
import android.view.inputmethod.InputMethodManager;
import android.view.SurfaceView;
import android.view.ViewGroup;
import android.view.View;
import android.widget.ImageView;
import android.widget.Toast;
import android.content.res.Resources.NotFoundException;

import org.libsdl.app.SDL;
import org.libsdl.app.SDLActivity;

import org.kivy.android.launcher.Project;

import org.renpy.android.ResourceManager;


public class PythonActivity extends SDLActivity {
    private static final String TAG = "PythonActivity";

    public static PythonActivity mActivity = null;

    private ResourceManager resourceManager = null;
    private Bundle mMetaData = null;
    private PowerManager.WakeLock mWakeLock = null;

    @Override
    protected int getInitSubsystems() {
        // Samsung A035F returns garbage bytes in sensor names (Modified UTF-8 illegal byte 0x91).
        // This causes a fatal JNI abort in SystemSensorManager.nativeGetSensorAtIndex.
        // Exclude SDL_INIT_SENSOR to prevent the Java bootstrap from enumerating sensors.
        return SDL.SDL_INIT_EVERYTHING & ~SDL.SDL_INIT_SENSOR;
    }

    public String getAppRoot() {
        String app_root =  getFilesDir().getAbsolutePath() + "/app";
        return app_root;
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        Log.v(TAG, "PythonActivity onCreate running");
        resourceManager = new ResourceManager(this);

        Log.v(TAG, "About to do super onCreate");
        super.onCreate(savedInstanceState);
        Log.v(TAG, "Did super onCreate");

        this.mActivity = this;
        this.showLoadingScreen(this.getLoadingScreen());

        new UnpackFilesTask().execute(getAppRoot());
    }

    public void loadLibraries() {
        String app_root = new String(getAppRoot());
        File app_root_file = new File(app_root);
        PythonUtil.loadLibraries(app_root_file,
            new File(getApplicationInfo().nativeLibraryDir));
    }

    public void toastError(final String msg) {

        final Activity thisActivity = this;

        runOnUiThread(new Runnable () {
            public void run() {
                Toast.makeText(thisActivity, msg, Toast.LENGTH_LONG).show();
            }
        });

        synchronized (this) {
            try {
                this.wait(1000);
            } catch (InterruptedException e) {
            }
        }
    }

    private class UnpackFilesTask extends AsyncTask<String, Void, String> {
        @Override
        protected String doInBackground(String... params) {
            File app_root_file = new File(params[0]);
            Log.v(TAG, "Ready to unpack");
            PythonUtil.unpackAsset(mActivity, "private", app_root_file, true);
            PythonUtil.unpackPyBundle(mActivity, getApplicationInfo().nativeLibraryDir + "/" + "libpybundle", app_root_file, false);
            return null;
        }

        @Override
        protected void onPostExecute(String result) {
            mActivity.finishLoad();

            mActivity.showLoadingScreen(getLoadingScreen());

            String app_root_dir = getAppRoot();
            if (getIntent() != null && getIntent().getAction() != null &&
                    getIntent().getAction().equals("org.kivy.LAUNCH")) {
                File path = new File(getIntent().getData().getSchemeSpecificPart());

                Project p = Project.scanDirectory(path);
                String entry_point = getEntryPoint(p.dir);
                SDLActivity.nativeSetenv("ANDROID_ENTRYPOINT", p.dir + "/" + entry_point);
                SDLActivity.nativeSetenv("ANDROID_ARGUMENT", p.dir);
                SDLActivity.nativeSetenv("ANDROID_APP_PATH", p.dir);

                if (p != null) {
                    if (p.landscape) {
                        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE);
                    } else {
                        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);
                    }
                }

                try {
                    FileWriter f = new FileWriter(new File(path, ".launch"));
                    f.write("started");
                    f.close();
                } catch (IOException e) {
                }
            } else {
                String entry_point = getEntryPoint(app_root_dir);
                SDLActivity.nativeSetenv("ANDROID_ENTRYPOINT", entry_point);
                SDLActivity.nativeSetenv("ANDROID_ARGUMENT", app_root_dir);
                SDLActivity.nativeSetenv("ANDROID_APP_PATH", app_root_dir);
            }

            String mFilesDirectory = mActivity.getFilesDir().getAbsolutePath();
            Log.v(TAG, "Setting env vars for start.c and Python to use");
            SDLActivity.nativeSetenv("ANDROID_PRIVATE", mFilesDirectory);
            SDLActivity.nativeSetenv("ANDROID_UNPACK", app_root_dir);
            SDLActivity.nativeSetenv("PYTHONHOME", app_root_dir);
            SDLActivity.nativeSetenv("PYTHONPATH", app_root_dir + ":" + app_root_dir + "/lib");
            SDLActivity.nativeSetenv("PYTHONOPTIMIZE", "2");

            try {
                Log.v(TAG, "Access to our meta-data...");
                mActivity.mMetaData = mActivity.getPackageManager().getApplicationInfo(
                        mActivity.getPackageName(), PackageManager.GET_META_DATA).metaData;

                PowerManager pm = (PowerManager) mActivity.getSystemService(Context.POWER_SERVICE);
                if ( mActivity.mMetaData.getInt("wakelock") == 1 ) {
                    mActivity.mWakeLock = pm.newWakeLock(PowerManager.SCREEN_BRIGHT_WAKE_LOCK, "Screen On");
                    mActivity.mWakeLock.acquire();
                }
                if ( mActivity.mMetaData.getInt("surface.transparent") != 0 ) {
                    Log.v(TAG, "Surface will be transparent.");
                    getSurface().setZOrderOnTop(true);
                    getSurface().getHolder().setFormat(PixelFormat.TRANSPARENT);
                } else {
                    Log.i(TAG, "Surface will NOT be transparent");
                }
            } catch (PackageManager.NameNotFoundException e) {
            }

            if (mActivity.mHasFocus && (
                    mActivity.mCurrentNativeState == NativeState.INIT ||
                    (
                    mActivity.mCurrentNativeState == NativeState.RESUMED &&
                    mActivity.mSDLThread == null
                    ))) {
                mActivity.resumeNativeThread();
            }
        }

        @Override
        protected void onPreExecute() {
        }

        @Override
        protected void onProgressUpdate(Void... values) {
        }
    }

    public static ViewGroup getLayout() {
        return   mLayout;
    }

    public static SurfaceView getSurface() {
        return   mSurface;
    }

    public interface NewIntentListener {
        void onNewIntent(Intent intent);
    }

    private List<NewIntentListener> newIntentListeners = null;

    public void registerNewIntentListener(NewIntentListener listener) {
        if ( this.newIntentListeners == null )
            this.newIntentListeners = Collections.synchronizedList(new ArrayList<NewIntentListener>());
        this.newIntentListeners.add(listener);
    }

    public void unregisterNewIntentListener(NewIntentListener listener) {
        if ( this.newIntentListeners == null )
            return;
        this.newIntentListeners.remove(listener);
    }

    @Override
    protected void onNewIntent(Intent intent) {
        if ( this.newIntentListeners == null )
            return;
        this.onResume();
        synchronized ( this.newIntentListeners ) {
            Iterator<NewIntentListener> iterator = this.newIntentListeners.iterator();
            while ( iterator.hasNext() ) {
                (iterator.next()).onNewIntent(intent);
            }
        }
    }

    public interface ActivityResultListener {
        void onActivityResult(int requestCode, int resultCode, Intent data);
    }

    private List<ActivityResultListener> activityResultListeners = null;

    public void registerActivityResultListener(ActivityResultListener listener) {
        if ( this.activityResultListeners == null )
            this.activityResultListeners = Collections.synchronizedList(new ArrayList<ActivityResultListener>());
        this.activityResultListeners.add(listener);
    }

    public void unregisterActivityResultListener(ActivityResultListener listener) {
        if ( this.activityResultListeners == null )
            return;
        this.activityResultListeners.remove(listener);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent intent) {
        if ( this.activityResultListeners == null )
            return;
        this.onResume();
        synchronized ( this.activityResultListeners ) {
            Iterator<ActivityResultListener> iterator = this.activityResultListeners.iterator();
            while ( iterator.hasNext() )
                (iterator.next()).onActivityResult(requestCode, resultCode, intent);
        }
    }

    public static void start_service(
            String serviceTitle,
            String serviceDescription,
            String pythonServiceArgument
            ) {
        _do_start_service(
            serviceTitle, serviceDescription, pythonServiceArgument, true
        );
    }

    public static void start_service_not_as_foreground(
            String serviceTitle,
            String serviceDescription,
            String pythonServiceArgument
            ) {
        _do_start_service(
            serviceTitle, serviceDescription, pythonServiceArgument, false
        );
    }

    public static void _do_start_service(
            String serviceTitle,
            String serviceDescription,
            String pythonServiceArgument,
            boolean showForegroundNotification
            ) {
        Intent serviceIntent = new Intent(PythonActivity.mActivity, PythonService.class);
        String argument = PythonActivity.mActivity.getFilesDir().getAbsolutePath();
        String app_root_dir = PythonActivity.mActivity.getAppRoot();
        String entry_point = PythonActivity.mActivity.getEntryPoint(app_root_dir + "/service");
        serviceIntent.putExtra("androidPrivate", argument);
        serviceIntent.putExtra("androidArgument", app_root_dir);
        serviceIntent.putExtra("serviceEntrypoint", "service/" + entry_point);
        serviceIntent.putExtra("pythonName", "python");
        serviceIntent.putExtra("pythonHome", app_root_dir);
        serviceIntent.putExtra("pythonPath", app_root_dir + ":" + app_root_dir + "/lib");
        serviceIntent.putExtra("serviceStartAsForeground",
            (showForegroundNotification ? "true" : "false")
        );
        serviceIntent.putExtra("serviceTitle", serviceTitle);
        serviceIntent.putExtra("serviceDescription", serviceDescription);
        serviceIntent.putExtra("pythonServiceArgument", pythonServiceArgument);
        PythonActivity.mActivity.startService(serviceIntent);
    }

    public static void stop_service() {
        Intent serviceIntent = new Intent(PythonActivity.mActivity, PythonService.class);
        PythonActivity.mActivity.stopService(serviceIntent);
    }

    public static ImageView mImageView = null;
    public static View mLottieView = null;
    protected boolean mAppConfirmedActive = false;
    protected Timer loadingScreenRemovalTimer = null; 

    @Override
    protected boolean sendCommand(int command, Object data) {
        boolean result = super.sendCommand(command, data);
        considerLoadingScreenRemoval();
        return result;
    }
   
    @Override
    public void appConfirmedActive() {
        if (!mAppConfirmedActive) {
            Log.v(TAG, "appConfirmedActive() -> preparing loading screen removal");
            mAppConfirmedActive = true;
            considerLoadingScreenRemoval();
        }
    }

    public void considerLoadingScreenRemoval() {
        if (loadingScreenRemovalTimer != null)
            return;
        runOnUiThread(new Runnable() {
            public void run() {
                if (((PythonActivity)PythonActivity.mSingleton).mAppConfirmedActive &&
                        loadingScreenRemovalTimer == null) {
                    TimerTask removalTask = new TimerTask() {
                        @Override
                        public void run() {
                            runOnUiThread(new Runnable() {
                                @Override
                                public void run() {
                                    PythonActivity activity =
                                        ((PythonActivity)PythonActivity.mSingleton);
                                    if (activity != null)
                                        activity.removeLoadingScreen();
                                }
                            });
                        }
                    };
                    loadingScreenRemovalTimer = new Timer();
                    loadingScreenRemovalTimer.schedule(removalTask, 5000);
                }
            }
        });
    }

    public void removeLoadingScreen() {
        runOnUiThread(new Runnable() {
            public void run() {
                View view = mLottieView != null ? mLottieView : mImageView;
                if (view != null && view.getParent() != null) {
                    ((ViewGroup)view.getParent()).removeView(view);
                    mLottieView = null;
                    mImageView = null;
                }
            }
        });
    }

    public String getEntryPoint(String search_dir) {
        List<String> entryPoints = new ArrayList<String>();
        entryPoints.add("main.pyc");
        for (String value : entryPoints) {
            File mainFile = new File(search_dir + "/" + value);
            if (mainFile.exists()) {
                return value;
            }
        }
        return "main.py";
    }

    protected void showLoadingScreen(View view) {
        try {
            if (mLayout == null) {
                setContentView(view);
            } else if (view.getParent() == null) {
                mLayout.addView(view);
            }
        } catch (IllegalStateException e) {
        }
    }

    protected void setBackgroundColor(View view) {
        String backgroundColor = resourceManager.getString("presplash_color");
        if (backgroundColor != null) {
            try {
                view.setBackgroundColor(Color.parseColor(backgroundColor));
            } catch (IllegalArgumentException e) {}
        }
    }

    protected View getLoadingScreen() {
        if (mLottieView != null || mImageView != null) {
            return mLottieView != null ? mLottieView : mImageView;
        }

        try {
            mLottieView = getLayoutInflater().inflate(
                this.resourceManager.getIdentifier("lottie", "layout"),
                mLayout,
                false
            );
            try {
                if (mLayout == null) {
                    setContentView(mLottieView);
                } else if (PythonActivity.mLottieView.getParent() == null) {
                    mLayout.addView(mLottieView);
                }
            } catch (IllegalStateException e) {
            }
            setBackgroundColor(mLottieView);
            return mLottieView;
        }
        catch (NotFoundException e) {
            Log.v("SDL", "couldn't find lottie layout or animation, trying static splash");
        }

        int presplashId = this.resourceManager.getIdentifier("presplash", "drawable");
        InputStream is = this.getResources().openRawResource(presplashId);
        Bitmap bitmap = null;
        try {
            bitmap = BitmapFactory.decodeStream(is);
        } finally {
            try {
                is.close();
            } catch (IOException e) {};
        }

        mImageView = new ImageView(this);
        mImageView.setImageBitmap(bitmap);
        setBackgroundColor(mImageView);

        mImageView.setLayoutParams(new ViewGroup.LayoutParams(
            ViewGroup.LayoutParams.FILL_PARENT,
            ViewGroup.LayoutParams.FILL_PARENT));
        mImageView.setScaleType(ImageView.ScaleType.FIT_CENTER);
        return mImageView;
    }

    @Override
    protected void onPause() {
        if (this.mWakeLock != null && mWakeLock.isHeld()) {
            this.mWakeLock.release();
        }

        Log.v(TAG, "onPause()");
        try {
            super.onPause();
        } catch (UnsatisfiedLinkError e) {
        }
    }

    @Override
    protected void onResume() {
        if (this.mWakeLock != null) {
            this.mWakeLock.acquire();
        }
        Log.v(TAG, "onResume()");
        try {
            super.onResume();
        } catch (UnsatisfiedLinkError e) {
        }
        considerLoadingScreenRemoval();
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        try {
            super.onWindowFocusChanged(hasFocus);
        } catch (UnsatisfiedLinkError e) {
        }
        considerLoadingScreenRemoval();
    }

    public interface PermissionsCallback {
        void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults);
    }

    private PermissionsCallback permissionCallback;
    private boolean havePermissionsCallback = false;

    public void addPermissionsCallback(PermissionsCallback callback) {
        permissionCallback = callback;
        havePermissionsCallback = true;
        Log.v(TAG, "addPermissionsCallback(): Added callback for onRequestPermissionsResult");
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        Log.v(TAG, "onRequestPermissionsResult()");
        if (havePermissionsCallback) {
            Log.v(TAG, "onRequestPermissionsResult passed to callback");
            permissionCallback.onRequestPermissionsResult(requestCode, permissions, grantResults);
        }
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
    }

    public boolean checkCurrentPermission(String permission) {
        if (android.os.Build.VERSION.SDK_INT < 23)
            return true;

        try {
            java.lang.reflect.Method methodCheckPermission =
                Activity.class.getMethod("checkSelfPermission", String.class);
            Object resultObj = methodCheckPermission.invoke(this, permission);
            int result = Integer.parseInt(resultObj.toString());
            if (result == PackageManager.PERMISSION_GRANTED) 
                return true;
        } catch (IllegalAccessException | NoSuchMethodException |
                 InvocationTargetException e) {
        }
        return false;
    }

    public void requestPermissionsWithRequestCode(String[] permissions, int requestCode) {
        if (android.os.Build.VERSION.SDK_INT < 23)
            return;
        try {
            java.lang.reflect.Method methodRequestPermission =
                Activity.class.getMethod("requestPermissions",
                String[].class, int.class);
            methodRequestPermission.invoke(this, permissions, requestCode);
        } catch (IllegalAccessException | NoSuchMethodException |
                 InvocationTargetException e) {
        }
    }

    public void requestPermissions(String[] permissions) {
        requestPermissionsWithRequestCode(permissions, 1);
    }

    public static void changeKeyboard(int inputType) {
      if (SDLActivity.keyboardInputType != inputType){
          SDLActivity.keyboardInputType = inputType;
          InputMethodManager imm = (InputMethodManager) getContext().getSystemService(Context.INPUT_METHOD_SERVICE);
          imm.restartInput(mTextEdit);
          }
    }
}
