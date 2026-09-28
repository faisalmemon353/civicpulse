import http from "k6/http";
import { check, sleep } from "k6";

// CivicPulse HPA Scale-out Load Generation Script
// Ramps load to exceed the CPU 60% target threshold on backend replicas

export const options = {
  stages: [
    { duration: "30s", target: 10 },  // Baseline traffic
    { duration: "1m",  target: 50 },  // Ramp-up to trigger HPA scale-out
    { duration: "2m",  target: 100 }, // Sustained heavy load (reaches max replicas)
    { duration: "30s", target: 20 },  // Traffic reduction
    { duration: "30s", target: 0 },   // Cool-down
  ],
  thresholds: {
    http_req_failed: ["rate<0.05"], // Less than 5% errors
    http_req_duration: ["p(95)<2000"], // 95% of requests within 2 seconds
  },
};

const BASE_URL = __ENV.TARGET_URL || "http://localhost:8000";

const SAMPLE_COMPLAINTS = [
  {
    text: "Pani ka pipeline phat gaya hai, poori gali paani se bhar gayi hai aur gharon me ja raha hai.",
    location: "Street 14, Block 4, Clifton",
  },
  {
    text: "Main transformer tripped with loud bang around 3am. Whole area without light in extreme heat.",
    location: "Sector G-9/2, Islamabad",
  },
  {
    text: "Garbage dump not cleared for past ten days. Stray dogs tearing bags, severe stench across market.",
    location: "Bazaar Road, Saddar",
  },
  {
    text: "Deep open pothole on main road causing accidents daily. Two motorcycle riders fell last evening.",
    location: "Near Metro Station, Ring Road",
  },
  {
    text: "Streetlights on the main avenue have been off for three weeks straight. Unsafe for women walking at night.",
    location: "Street 7, Phase 5, DHA",
  },
];

export default function () {
  // 1. Submit a complaint
  const sample = SAMPLE_COMPLAINTS[Math.floor(Math.random() * SAMPLE_COMPLAINTS.length)];
  const postPayload = JSON.stringify({
    text: sample.text,
    location: sample.location,
    reporter_contact: "citizen@example.com",
  });

  const postParams = {
    headers: {
      "Content-Type": "application/json",
      "X-Request-ID": `k6-${__VU}-${__ITER}-${Date.now()}`,
    },
  };

  const postRes = http.post(`${BASE_URL}/api/complaints`, postPayload, postParams);
  check(postRes, {
    "complaint submission returned 201 or 429": (r) => r.status === 201 || r.status === 429,
  });

  // 2. Fetch stats (exercises Redis cache read-through and invalidation)
  const statsRes = http.get(`${BASE_URL}/api/stats`);
  check(statsRes, {
    "stats returned 200": (r) => r.status === 200,
    "stats has X-Cache header": (r) => r.headers["X-Cache"] !== undefined,
  });

  // 3. Query complaints list
  const listRes = http.get(`${BASE_URL}/api/complaints?page=1&page_size=10`);
  check(listRes, {
    "complaints list returned 200": (r) => r.status === 200,
  });

  sleep(0.5);
}
