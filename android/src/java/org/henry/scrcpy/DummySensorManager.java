package org.henry.scrcpy;

import android.hardware.Sensor;
import android.hardware.SensorAdditionalInfo;
import android.hardware.SensorDirectChannel;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.hardware.HardwareBuffer;
import android.os.Handler;
import android.os.MemoryFile;

import java.util.Collections;
import java.util.List;

public class DummySensorManager extends SensorManager {
    @Override
    public List<Sensor> getSensorList(int type) {
        return Collections.emptyList();
    }

    @Override
    public Sensor getDefaultSensor(int type) {
        return null;
    }

    @Override
    public Sensor getDefaultSensor(int type, boolean wakeUp) {
        return null;
    }

    @Override
    protected List<Sensor> getFullSensorList() {
        return Collections.emptyList();
    }

    @Override
    protected List<Sensor> getFullDynamicSensorList() {
        return Collections.emptyList();
    }

    @Override
    protected boolean registerListenerImpl(SensorEventListener listener, Sensor sensor, int delayUs, Handler handler, int maxBatchReportLatencyUs, int reservedFlags) {
        return false;
    }

    @Override
    protected void unregisterListenerImpl(SensorEventListener listener, Sensor sensor) {
    }

    @Override
    protected boolean flushImpl(SensorEventListener listener) {
        return false;
    }

    @Override
    protected boolean initDataInjectionImpl(boolean enable, int reserved) {
        return false;
    }

    @Override
    protected boolean injectSensorDataImpl(Sensor sensor, float[] values, int accuracy, long timestamp) {
        return false;
    }

    @Override
    protected boolean setOperationParameterImpl(SensorAdditionalInfo parameter) {
        return false;
    }

    @Override
    protected SensorDirectChannel createDirectChannelImpl(MemoryFile memoryFile, HardwareBuffer hardwareBuffer) {
        return null;
    }

    @Override
    protected void destroyDirectChannelImpl(SensorDirectChannel channel) {
    }

    @Override
    protected int configureDirectChannelImpl(SensorDirectChannel channel, Sensor sensor, int rateLevel) {
        return 0;
    }
}
