package com.gsi

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.gsi.ui.GsiArchiveScreen
import com.gsi.ui.theme.GSITheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Android 15/16/17 Edge-to-Edge:
        // Translucent/transparent status and navigation bars so content bleeds edge-to-edge
        enableEdgeToEdge()

        setContent {
            GSITheme {
                GsiArchiveScreen()
            }
        }
    }
}
