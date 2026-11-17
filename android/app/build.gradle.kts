plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
}

val archiveRoot = rootProject.projectDir.parentFile
val reviewAssetsDir = layout.buildDirectory.dir("generated/gsi-review-assets")
val reviewAsset = reviewAssetsDir.map { it.file("data/reviews.json") }
val exportAndroidReviews = tasks.register<Exec>("exportAndroidReviews") {
    val catalog = file("src/main/assets/data/catalog.json")
    val entries = File(archiveRoot, "entries")
    val exporter = File(archiveRoot, "tools/export_android_reviews.py")
    inputs.file(catalog)
    inputs.files(fileTree(entries) { include("*.md") })
    inputs.file(exporter)
    inputs.file(File(archiveRoot, "builder/entry_pages.py"))
    outputs.file(reviewAsset)
    workingDir(archiveRoot)
    commandLine(
        "python", "-B", exporter.absolutePath,
        "--catalog", catalog.absolutePath,
        "--entries", entries.absolutePath,
        "--output", reviewAsset.get().asFile.absolutePath
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
        versionCode = 1
        versionName = "1.0"

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
    sourceSets.getByName("main").assets.srcDir(reviewAssetsDir.get().asFile)
}

tasks.named("preBuild") { dependsOn(exportAndroidReviews) }

dependencies {
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    testImplementation(libs.junit)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(libs.androidx.junit)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
    debugImplementation(libs.androidx.compose.ui.tooling)
}
