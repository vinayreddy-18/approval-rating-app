import { getApps, initializeApp } from "https://www.gstatic.com/firebasejs/10.13.0/firebase-app.js";
import { getAuth, GoogleAuthProvider, signInWithPopup, signOut } from "https://www.gstatic.com/firebasejs/10.13.0/firebase-auth.js";

const firebaseConfig = {
  apiKey: "AIzaSyBwgaj3xi4T5MJac2GTuA-HshPIKErLRl8",
  authDomain: "approval-rating-app.firebaseapp.com",
  projectId: "approval-rating-app",
  storageBucket: "approval-rating-app.appspot.com",
  messagingSenderId: "255711587084",
  appId: "1:255711587084:web:8961d27d9a546cc6afb729",
  measurementId: "G-KW26MP967X"
};

console.log("Firebase config loaded:", firebaseConfig);

const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
const auth = getAuth(app);
const provider = new GoogleAuthProvider();

const postLoginToBackend = async (user) => {
  const response = await fetch("/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ uid: user.uid, email: user.email })
  });

  if (!response.ok) {
    throw new Error("Unable to complete sign-in");
  }

  localStorage.setItem("firebase-uid", user.uid);
  localStorage.setItem("firebase-email", user.email || "");

  const params = new URLSearchParams({ email: user.email || "", uid: user.uid });
  window.location.href = `/dashboard?${params.toString()}`;
};

const handleLogin = async () => {
  try {
    const result = await signInWithPopup(auth, provider);
    await postLoginToBackend(result.user);
  } catch (error) {
    console.error(error);
    window.alert("Sign-in failed. Please try again.");
  }
};

const handleLogout = async () => {
  try {
    await signOut(auth);
    localStorage.removeItem("firebase-uid");
    localStorage.removeItem("firebase-email");
    window.location.href = "/";
  } catch (error) {
    console.error(error);
  }
};

document.addEventListener("DOMContentLoaded", () => {
  const loginButton = document.getElementById("login-btn");
  const logoutButton = document.getElementById("logout-btn");

  if (loginButton) {
    loginButton.addEventListener("click", handleLogin);
  }

  if (logoutButton) {
    logoutButton.addEventListener("click", handleLogout);
  }
});
