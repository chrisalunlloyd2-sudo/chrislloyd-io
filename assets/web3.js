/**
 * web3.js — optional "flex" module. Entirely isolated from the rest of the site.
 *
 * Scope (read-only, cosmetic):
 *   - "Connect Wallet" button (read-only): shows connected address + ENS name/avatar.
 *   - Optional owner ENS badge in the footer (verified-identity flex).
 *
 * Safety rails (do not remove):
 *   - Feature-flagged OFF via data/config.json "web3FlexEnabled".
 *   - Read-only: only eth_requestAccounts (address) + reverse-lookup fetches.
 *     NEVER eth_sign, signing, token approvals, or any transaction.
 *   - No seed phrase / private key handling of any kind, ever.
 *   - No state persistence: nothing is stored (no cookies/localStorage).
 *   - Failure here can never break the rest of the site: nothing outside this
 *     module is touched, and all errors are swallowed/logged to console only.
 *
 * Wallet library is loaded from a reputable CDN on demand (esm.sh, which
 * proxies the official npm package). Nothing is bundled, nothing runs until
 * the user clicks "Connect Wallet".
 */

const CONFIG_URL = "data/config.json";
const ENS_LIB_URL = "https://esm.sh/viem@2";
const CONNECT_BUTTON_ID = "web3-connect";
const BADGE_ID = "web3-owner-badge";

// --- helpers -------------------------------------------------------------

function $(id) { return document.getElementById(id); }

function shortAddr(addr) {
  return addr ? addr.slice(0, 6) + "…" + addr.slice(-4) : "";
}

// --- owner ENS badge (no wallet interaction needed) ----------------------

async function renderOwnerBadge(ens) {
  const badge = $(BADGE_ID);
  if (!badge || !ens) return;
  try {
    // viem is loaded on demand only when the badge has something to show.
    const { createPublicClient, http } = await import(ENS_LIB_URL);
    const client = createPublicClient({ chain: (await import(ENS_LIB_URL + "/chains")).mainnet, transport: http() });
    const [address, avatar] = await Promise.all([
      client.getEnsAddress({ name: ens }),
      client.getEnsAvatar({ name: ens }),
    ]);
    if (!address) throw new Error("ENS name does not resolve to an address");
    const img = document.createElement("img");
    img.src = avatar;
    img.alt = ens + " avatar";
    img.width = 22;
    img.height = 22;
    img.style.cssText = "vertical-align:middle;border-radius:50%;margin-right:6px;";
    const label = document.createElement("span");
    label.textContent = "✓ " + ens;
    badge.appendChild(img);
    badge.appendChild(label);
    badge.hidden = false;
  } catch (err) {
    console.info("[web3] owner badge skipped:", err && err.message);
  }
}

// --- visitor "who's viewing" flex ---------------------------------------

async function connectWallet() {
  if (!window.ethereum) {
    alert("No Ethereum wallet found. Install MetaMask or similar to try this out.");
    return;
  }
  // Read-only permission request: address only. No signing, no approvals.
  const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
  const address = accounts && accounts[0];
  if (!address) return;
  const { createPublicClient, http, normalize } = await import(ENS_LIB_URL);
  const { mainnet } = await import(ENS_LIB_URL + "/chains");
  const client = createPublicClient({ chain: mainnet, transport: http() });
  let ensName = null;
  let avatar = null;
  try {
    ensName = await client.getEnsName({ address });
    if (ensName) {
      // Sanity-check the forward resolution (prevents spoofed reverse records).
      const forward = await client.getEnsAddress({ name: ensName });
      if (forward && forward.toLowerCase() === address.toLowerCase()) {
        avatar = await client.getEnsAvatar({ name: ensName });
      } else {
        ensName = null;
      }
    }
  } catch (err) {
    console.info("[web3] ENS lookup skipped:", err && err.message);
  }
  const btn = $(CONNECT_BUTTON_ID);
  if (btn) {
    btn.textContent = (ensName ? ensName : shortAddr(address)) + (avatar ? " " : "");
    if (avatar) {
      const img = document.createElement("img");
      img.src = avatar;
      img.alt = "";
      img.width = 18;
      img.height = 18;
      img.style.cssText = "vertical-align:middle;border-radius:50%;margin-left:6px;";
      btn.appendChild(img);
    }
    btn.disabled = true;
  }
}

// --- boot ----------------------------------------------------------------

async function boot() {
  let cfg;
  try {
    cfg = await (await fetch(CONFIG_URL)).json();
  } catch (err) {
    console.info("[web3] config unavailable; module staying dormant.", err && err.message);
    return;
  }
  if (!cfg || cfg.web3FlexEnabled !== true) return; // feature flag: OFF by default

  // 1) Owner badge (if an ENS name is configured and it actually resolves).
  const ownerEns = (cfg.web3 && cfg.web3.ownerEns) || "";
  if (ownerEns) await renderOwnerBadge(ownerEns);

  // 2) Visitor connect button.
  const btn = document.createElement("button");
  btn.id = CONNECT_BUTTON_ID;
  btn.className = "web3-connect-btn";
  btn.textContent = "🦊 Connect Wallet";
  btn.type = "button";
  btn.addEventListener("click", () => {
    connectWallet().catch((err) => {
      console.info("[web3] connect cancelled/failed:", err && err.message);
      const b = $(CONNECT_BUTTON_ID);
      if (b) b.textContent = "🦊 Connect Wallet";
    });
  });
  btn.style.cssText = [
    "display:inline-block",
    "padding:8px 16px",
    "border:1px solid rgba(255,255,255,.5)",
    "border-radius:999px",
    "background:transparent",
    "color:#fff",
    "font:inherit",
    "font-size:.9rem",
    "font-weight:600",
    "cursor:pointer",
  ].join(";");
  const holder = $("web3-flex-holder") || document.querySelector(".hero .wrap");
  if (holder) holder.appendChild(btn);
}

boot().catch((err) => console.info("[web3] dormant:", err && err.message));