/**
 * The sound a Strategist hears when a Handover Request arrives.
 *
 * Inline, as a `data:` URI, rather than a file in `public/`: the Console must make a noise the
 * first time a request lands, and a fetch for a sound file is one more thing that can be
 * blocked, cached wrongly, or missing from a build. It is a 200 ms two-tone blip — 8-bit,
 * 8 kHz, mono — which is 1.6 kB of WAV and about 2 kB of base64, cheaper than the HTTP request
 * that would have fetched it.
 *
 * Generated with:
 *
 *     python3 - <<'PY'
 *     import base64, math, struct
 *     rate, samples = 8000, bytearray()
 *     for freq, ms in ((880, 90), (1320, 110)):
 *         n = int(rate * ms / 1000)
 *         for i in range(n):
 *             env = min(1.0, i / 60, (n - i) / 60)   # no click at either end
 *             samples.append(int(128 + math.sin(2 * math.pi * freq * i / rate) * env * 0.55 * 110))
 *     data = bytes(samples)
 *     wav = (b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE"
 *            + b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate, 1, 8)
 *            + b"data" + struct.pack("<I", len(data)) + data)
 *     print(base64.b64encode(wav).decode())
 *     PY
 */
export const NOTIFICATION_SOUND =
  'data:audio/wav;base64,' +
  'UklGRmQGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YUAGAACAgIGCgX56eHp/hYqKhXxzb3N9ipOT' +
  'inttZmt6jZuckHtnXWN2j6Kml31jVFpxkamvn39fTFFrka+5qINcRUlmj7C8rIdfRkdii668rotiR0Zfh6y8sI9m' +
  'SUVcg6m8s5JpSkRZgKa7tZZtTENWfKO6tplwT0NTeKC5uJ10UUNRdJ24uaB4U0NPcJm2uqN8VkNMbZa1u6aAWURK' +
  'aZKzvKmDXEVJZo+wvKyHX0ZHYouuvK6LYkdGX4esvLCPZklFXIOpvLOSaUpEWYCmu7WWbUxDVnyjuraZcE9DU3ig' +
  'ubiddFFDUXSduLmgeFNDT3CZtrqjfFZDTG2Wtbumf1lESmmSs7ypg1xFSWaPsLysh19GR2KLrryui2JHRl+HrLyw' +
  'j2ZJRVyDqbyzkmlKRFl/pru1lm1MQ1Z8o7q2mXBPQ1N4oLm4nXRRQ1F0nbi5oHhTQ09wmba6o3xWQ0xtlrW7pn9Z' +
  'REppkrO8qYNcRUlmj7C8rIdfRkdii668rotiR0Zfh6y8sI9mSUVcg6m8s5JpSkRZgKa7tZZtTENWfKO6tplwT0NT' +
  'eKC5uJ10UUNRdJ24uaB4U0NPcJm2uqN8VkNMbZa1u6Z/WURKaZKzvKmDXEVJZo+wvKyHX0ZHYouuvK6LYkdGX4es' +
  'vLCPZklFXIOpvLOSaUpEWYCmu7WWbUxDVnyjuraZcE9DU3igubiddFFDUXSduLmgeFNDT3CZtrqjfFZDTG2Wtbum' +
  'f1lESmmSs7ypg1xFSWaPsLysh19GR2KLrryui2JHRl+HrLywj2ZJRVyDqbyzkmlKRFl/pru1lm1MQ1Z8o7q2mXBP' +
  'Q1N4oLm4nXRRQ1F0nbi5oHhTQ09wmba6o3xWQ0xtlrW7poBZREppkrO8qYNcRktnjqy2poZkUFJoiKOtoohrWVlq' +
  'hJuknIhxYmFugZOblod3a2pygIyRj4V7dHJ3f4WIh4N+e3t9f4CAgIGAfHt/hYeAd3V+io2Cc298jpOEb2l5kZmH' +
  'bGN2lJ+Lal1ylqaPaFZtmKyUZ1BombKaZkpimbigZ0RcmLylaURZlLuobURWkLqqcEVTjbmtdEdRibiveEhPhbay' +
  'fEpMgbW0gEtKfrO1g01JerC3h1BHdq64i1JGcqy6j1VFb6m7kldEa6a7llpDZ6O8mV1DZKC8nWFDYZ28oGRDXZm8' +
  'o2dDWpa7pmtEV5K7qW9FVY+6rHJGUou4rnZHUIe3sHpJTYO1s35KS3+0tYFMSnyytoVPSHivuIlRR3StuY1TRXCq' +
  'upBWRG2ou5RZRGmlvJhcQ2aivJtfQ2KevJ5iQ1+bvKJmQ1yYvKVpRFmUu6htRFaQuqpwRVONua10R1GJuK94SE+F' +
  'trJ8SkyBtbSAS0p+s7WDTUl6sLeHUEd2rriLUkZyrLqPVUVvqbuSV0RrpruWWkNno7yZXUNkoLydYUNhnbygZENd' +
  'mbyjZ0Nalruma0RXkrupb0VVj7qsckZSi7iudkdQh7eweklNg7WzfkpLf7S1gUxKfLK2hU9IeK+4iVFHdK25jVNF' +
  'cKq6kFZEbai7lFlEaaW8mFxDZqK8m19DYp68nmJDX5u8omZDXJi8pWlEWZS7qG1EVpC6qnBFU425rXRHUYm4r3hI' +
  'T4W2snxKTIG1tIBLSn6ztYNNSXqwt4dQR3auuItSRnKsuo9VRW+pu5JXRGumu5ZaQ2ejvJldQ2SgvJ1hQ2GdvKBk' +
  'Q12ZvKNnQ1qWu6ZrRFeSu6lvRVWPuqxyRlKLuK52R1CHt7B6SU2DtbN+Skt/tLWBTEp8sraFT0h4r7iJUUd0rbmN' +
  'U0VwqrqQVkRtqLuUWURppbyYXENmorybX0NinryeYkNfm7yiZkNcmLylaURZlLuobURWkLqqcEVTjbmtdEdRibiv' +
  'eEhPhbayfEpMgbW0gEtKfrO1g01JerC3h1BHdq64i1JGcqy6j1VFb6m7kldEa6a7llpDZ6O8mV1DZKC8nWFDYZ28' +
  'oGRDXZm8o2dDWpa7pmtEV5K7qW9FVY+6rHJGUou4rnZHUIe3sHpJTYO1s35KS3+0tYFMSnyytoVPSHivuIlRR3St' +
  'uYxVSHGntI5cTXCgr5BiU2+aqpBoWG+UpJBtXnCPno5yZHGLmI12anSHkop6cXeEi4d8d3qBhYN+fX6A'


/**
 * Play the blip, and never let it break the page.
 *
 * A browser refuses to play audio until the person has interacted with the page, and that
 * refusal is a rejected promise. The Strategist's own Availability toggle is that interaction
 * — which is also where the notification permission is asked for — so by the time a request
 * can arrive the sound is usually allowed. When it is not, the request still appears and the
 * notification still shows; only the noise is missing, and that is not worth an error.
 */
export function playNotificationSound(): void {
  try {
    void new Audio(NOTIFICATION_SOUND).play().catch(() => undefined)
  } catch {
    // No Audio in this environment (a test renderer, a locked-down browser).
  }
}
