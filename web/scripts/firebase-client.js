/*
 * Shared Firebase Web SDK client for Chaperone (GSI).
 * Works identically on static GitHub Pages and the local Node runtime.
 * Loads public web config from ../data/firebase-config.json (generated from firebase-applet-config.json).
 */
import { initializeApp, getApps } from "https://www.gstatic.com/firebasejs/11.6.1/firebase-app.js";
import {
  getFirestore,
  doc,
  setDoc,
  updateDoc,
  deleteDoc,
  getDocFromServer,
  getDocs,
  collection,
  query,
  orderBy,
  serverTimestamp,
} from "https://www.gstatic.com/firebasejs/11.6.1/firebase-firestore.js";
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  signOut,
  onAuthStateChanged,
} from "https://www.gstatic.com/firebasejs/11.6.1/firebase-auth.js";

export const OWNER_EMAIL = "cagri.ulas.6a@gmail.com";

export const OperationType = Object.freeze({
  CREATE: "create",
  UPDATE: "update",
  DELETE: "delete",
  LIST: "list",
  GET: "get",
  WRITE: "write",
});

let cachedServicesPromise = null;

function sanitizeString(value, maxLen) {
  return String(value ?? "").trim().slice(0, maxLen);
}

export function isValidSlug(slug) {
  return typeof slug === "string" && slug.length >= 1 && slug.length <= 120 && /^[a-z0-9-]+$/.test(slug);
}

export function isValidVisitorToken(token) {
  return typeof token === "string" && token.length >= 12 && token.length <= 48 && /^[a-zA-Z0-9_-]{12,48}$/.test(token);
}

export function handleFirestoreError(error, operationType, path, authInstance = null) {
  const user = authInstance?.currentUser || null;
  const errInfo = {
    error: error instanceof Error ? error.message : String(error),
    authInfo: {
      userId: user?.uid ?? null,
      email: user?.email ?? null,
      emailVerified: user?.emailVerified ?? null,
      isAnonymous: user?.isAnonymous ?? null,
      tenantId: user?.tenantId ?? null,
      providerInfo:
        user?.providerData?.map((provider) => ({
          providerId: provider.providerId,
          email: provider.email,
        })) || [],
    },
    operationType,
    path,
  };
  console.error("Firestore Error:", JSON.stringify(errInfo));
  throw new Error(JSON.stringify(errInfo));
}

async function loadFirebaseConfig() {
  const configUrl = new URL("../data/firebase-config.json", import.meta.url);
  const res = await fetch(configUrl.href, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Could not load Firebase web config (${res.status})`);
  }
  const cfg = await res.json();
  if (!cfg || !cfg.projectId || !cfg.apiKey) {
    throw new Error("Incomplete Firebase web configuration.");
  }
  return cfg;
}

async function testConnection(db) {
  try {
    await getDocFromServer(doc(db, "test", "connection"));
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    if (msg.includes("the client is offline")) {
      console.error("Please check your Firebase configuration (client appears offline).");
    }
  }
}

export function getFirebaseServices() {
  if (!cachedServicesPromise) {
    cachedServicesPromise = (async () => {
      const config = await loadFirebaseConfig();
      const app = getApps().length ? getApps()[0] : initializeApp(config);
      const db = config.firestoreDatabaseId
        ? getFirestore(app, config.firestoreDatabaseId)
        : getFirestore(app);
      const auth = getAuth(app);
      // Non-blocking startup connectivity check
      testConnection(db);
      return { app, db, auth, config };
    })();
  }
  return cachedServicesPromise;
}

export async function createVisitorHeart({ slug, pageType, track, artist, visitorToken }) {
  const cleanSlug = sanitizeString(slug, 120).toLowerCase();
  const cleanPageType = pageType === "p53" ? "p53" : "entry";
  const cleanTrack = sanitizeString(track, 160) || cleanSlug;
  const cleanArtist = sanitizeString(artist, 160) || "Unknown";
  const cleanToken = sanitizeString(visitorToken, 48);

  if (!isValidSlug(cleanSlug) || !isValidVisitorToken(cleanToken)) {
    throw new Error("Invalid heart identifier parameters.");
  }

  const { db, auth } = await getFirebaseServices();
  const heartId = `${cleanSlug}__${cleanToken}`;
  const path = `hearts/${heartId}`;
  const payload = {
    slug: cleanSlug,
    pageType: cleanPageType,
    track: cleanTrack,
    artist: cleanArtist,
    visitorToken: cleanToken,
    createdAt: serverTimestamp(),
    updatedAt: serverTimestamp(),
  };

  try {
    await setDoc(doc(db, "hearts", heartId), payload);
    return { heartId };
  } catch (error) {
    handleFirestoreError(error, OperationType.CREATE, path, auth);
  }
}

export async function attachVisitorHeartNote({ slug, visitorToken, note, senderName }) {
  const cleanSlug = sanitizeString(slug, 120).toLowerCase();
  const cleanToken = sanitizeString(visitorToken, 48);
  const cleanNote = sanitizeString(note, 400);
  const cleanSender = sanitizeString(senderName, 60);

  if (!isValidSlug(cleanSlug) || !isValidVisitorToken(cleanToken)) {
    throw new Error("Invalid heart identifier parameters.");
  }

  const { db, auth } = await getFirebaseServices();
  const heartId = `${cleanSlug}__${cleanToken}`;
  const path = `hearts/${heartId}`;
  const updates = {
    note: cleanNote,
    senderName: cleanSender,
    updatedAt: serverTimestamp(),
  };

  try {
    await updateDoc(doc(db, "hearts", heartId), updates);
    return { heartId };
  } catch (error) {
    handleFirestoreError(error, OperationType.UPDATE, path, auth);
  }
}

export async function removeVisitorHeart({ slug, visitorToken }) {
  const cleanSlug = sanitizeString(slug, 120).toLowerCase();
  const cleanToken = sanitizeString(visitorToken, 48);

  if (!isValidSlug(cleanSlug) || !isValidVisitorToken(cleanToken)) {
    throw new Error("Invalid heart identifier parameters.");
  }

  const { db, auth } = await getFirebaseServices();
  const heartId = `${cleanSlug}__${cleanToken}`;
  const path = `hearts/${heartId}`;

  try {
    await deleteDoc(doc(db, "hearts", heartId));
    return { heartId };
  } catch (error) {
    handleFirestoreError(error, OperationType.DELETE, path, auth);
  }
}

export async function signInOwnerWithGoogle() {
  const { auth } = await getFirebaseServices();
  const provider = new GoogleAuthProvider();
  provider.setCustomParameters({ prompt: "select_account" });
  return signInWithPopup(auth, provider);
}

export async function signOutOwner() {
  const { auth } = await getFirebaseServices();
  return signOut(auth);
}

export async function subscribeAuthState(callback) {
  const { auth } = await getFirebaseServices();
  return onAuthStateChanged(auth, callback);
}

export async function listAllHeartsForOwner() {
  const { db, auth } = await getFirebaseServices();
  const path = "hearts";
  try {
    const q = query(collection(db, path), orderBy("updatedAt", "desc"));
    const snap = await getDocs(q);
    return snap.docs.map((d) => {
      const data = d.data();
      return {
        id: d.id,
        slug: data.slug || "",
        pageType: data.pageType || "entry",
        track: data.track || "",
        artist: data.artist || "",
        note: data.note || "",
        senderName: data.senderName || "",
        createdAt: data.createdAt?.toDate ? data.createdAt.toDate().toISOString() : null,
        updatedAt: data.updatedAt?.toDate ? data.updatedAt.toDate().toISOString() : null,
      };
    });
  } catch (error) {
    handleFirestoreError(error, OperationType.LIST, path, auth);
  }
}
