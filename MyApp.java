package org.omer.odelia.odelia;

import android.app.Application;
import android.media.AudioManager;
import android.media.ToneGenerator;
import android.os.PowerManager;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.Socket;
import java.net.UnknownHostException;
import java.nio.ByteBuffer;

public class MyApp extends Application {
    void play_tone(ToneGenerator tone_generator, int tone) {
        tone_generator.startTone(tone);
        try {
            Thread.sleep(40);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        tone_generator.stopTone();
        try {
            Thread.sleep(40);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }

    @Override
    public void onCreate() {
        super.onCreate();
        new Thread() {
            @Override
            public void run() {
                // Make the device CPU always wake
                PowerManager powerManager = (PowerManager) getSystemService(POWER_SERVICE);
                PowerManager.WakeLock wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,
                        "MyWakelockTag");
                wakeLock.acquire();

                ToneGenerator tone_generator = new ToneGenerator(AudioManager.STREAM_MUSIC, 100);
                Socket socket = null;

                while (true) {
                    try {
                        socket = new Socket("odelia.zapto.org", 1221);

                        byte[] buffer = new byte[1024];
                        ByteBuffer wrapped = null;

                        InputStream inputStream = socket.getInputStream();
                        OutputStream outputStream = socket.getOutputStream();

                        while (true) {
                            if (-1 == inputStream.read(buffer, 0, 4)) {
                                break;
                            }
                            int size = wrapped.wrap(buffer).getInt();
                            if (-1 == inputStream.read(buffer, 0, size)) {
                                break;
                            }
                            int command = wrapped.wrap(buffer).get();
                            switch (command) {
                                case 0:
                                    play_tone(tone_generator, ToneGenerator.TONE_DTMF_8);
                                    break;
                                case 1:
                                    play_tone(tone_generator, ToneGenerator.TONE_DTMF_2);
                                    break;
                                case 2:
                                    play_tone(tone_generator, ToneGenerator.TONE_DTMF_6);
                                    break;
                                case 3:
                                    play_tone(tone_generator, ToneGenerator.TONE_DTMF_4);
                                    break;
                                case 4:
                                    play_tone(tone_generator, ToneGenerator.TONE_DTMF_5);
                                    break;
                            }
                        }

                    } catch (UnknownHostException e) {
                        e.printStackTrace();
                        // response = "UnknownHostException: " + e.toString();
                    } catch (IOException e) {
                        e.printStackTrace();
                        // response = "IOException: " + e.toString();
                    } catch (Exception e) {
                        e.printStackTrace();
                    } finally {
                        if (socket != null) {
                            try {
                                socket.close();
                                socket = null;
                            } catch (IOException e) {
                                // TODO Auto-generated catch block
                                e.printStackTrace();
                            }
                        }
                    }
                }
            }
        }.start();

        new Thread() {
            @Override
            public void run() {
                Socket socket = null;
                DatagramSocket socket2 = null;
                int bytes_read = -1;
                int total_bytes_read = -1;
                while (true) {
                    try {
                        socket = new Socket("127.0.0.1", 8080);
                        socket2 = new DatagramSocket();
                        InetAddress IPAddress =  InetAddress.getByName("odelia.zapto.org");

                        InputStream inputStream = socket.getInputStream();
                        OutputStream outputStream = socket.getOutputStream();
                        byte[] buffer = new byte[16000];
                        String get_image = "GET /video HTTP/1.1\r\n\r\n";
                        byte[] get_image_byte_array = get_image.getBytes();
                        outputStream.write(get_image_byte_array, 0, get_image_byte_array.length);
                        while (true) {
                            bytes_read = 0;
                            total_bytes_read = 0;
                            while (total_bytes_read < 16000) {
                                bytes_read = inputStream.read(buffer, total_bytes_read, 16000 - total_bytes_read);
                                if (-1 == bytes_read) {
                                    break;
                                };
                                total_bytes_read += bytes_read;
                            }

                            if (-1 == bytes_read) {
                                break;
                            };
                            DatagramPacket send_packet = new DatagramPacket(buffer, 16000, IPAddress, 1222);
                            socket2.send(send_packet);
                            Thread.sleep(5);
                        }
                    } catch (UnknownHostException e) {
                        e.printStackTrace();
                        // response = "UnknownHostException: " + e.toString();
                    } catch (IOException e) {
                        e.printStackTrace();
                        // response = "IOException: " + e.toString();
                    } catch (Exception e) {
                        e.printStackTrace();
                    } finally {
                        if (socket != null) {
                            try {
                                socket.close();
                                socket = null;
                                socket2.close();
                                socket2 = null;
                            } catch (IOException e) {
                                // TODO Auto-generated catch block
                                e.printStackTrace();
                            }
                        }
                    }
                }
            }
        }.start();
    }
}

