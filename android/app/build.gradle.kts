plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
}

val archiveRoot = rootProject.projectDir.parentFile
val nodeSyncScript = File(archiveRoot, "src/android-sync.mjs")

val syncAndroidArchive = tasks.register<Exec>("syncAndroidArchive") {
    val rootDirFile = archiveRoot
    val scriptFile = nodeSyncScript
    val siteCatalog = File(rootDirFile, "site/data/catalog.json")
    enabled = siteCatalog.isFile && scriptFile.isFile
    workingDir(rootDirFile)
    commandLine("node", scriptFile.absolutePath, "--sync-assets", "--root", rootDirFile.absolutePath)
}

val exportAndroidReviews = tasks.register<Exec>("exportAndroidReviews") {
    dependsOn(syncAndroidArchive)
    val rootDirFile = archiveRoot
    val scriptFile = nodeSyncScript
    val catalog = file("src/main/assets/data/catalog.json")
    val entries = File(rootDirFile, "entries")
    val reviewsOut = file("src/main/assets/data/reviews.json")
    enabled = catalog.isFile && scriptFile.isFile && entries.isDirectory
    inputs.file(catalog)
    inputs.files(fileTree(entries) { include("*.md") })
    inputs.file(scriptFile)
    outputs.file(reviewsOut)
    workingDir(rootDirFile)
    commandLine(
        "node", scriptFile.absolutePath,
        "--export-reviews",
        "--catalog", catalog.absolutePath,
        "--entries", entries.absolutePath,
        "--output", reviewsOut.absolutePath
    )
}

android {
    namespace = "com.gsi"
    compileSdk {
        version = release(37)
    }

    defaultConfig {
        applicationId = "com.gsi"
        minSdk = 37
        targetSdk = 37
        versionCode = 2
        versionName = "2.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            optimization {
                enable = true
                packageScope = setOf("androidx.**", "kotlin.**", "kotlinx.**")
            }
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    buildFeatures {
        compose = true
    }
}

tasks.named("preBuild") { dependsOn(exportAndroidReviews) }

dependencies {
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.compose.animation)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.material.icons.extended)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.media3.exoplayer)
    implementation(libs.androidx.glance.appwidget)
    implementation(libs.androidx.glance.material3)
    testImplementation(libs.junit)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(libs.androidx.junit)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
    debugImplementation(libs.androidx.compose.ui.tooling)
}
