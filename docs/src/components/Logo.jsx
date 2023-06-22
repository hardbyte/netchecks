function LogomarkPaths() {
  return (
    <g fill="none" strokeLinejoin="round" strokeWidth={1}>
     <circle id="primary" className="st0" cx="12.26" cy="12" r="9.79" style={{fill: "#2563EB"}}/>
  <path
     id="secondary"
     d="m 12,15 c -0.265803,0.0015 -0.521281,-0.102813 -0.71,-0.29 l -4,-4 C 6.3433337,9.7633337 7.7633337,8.3433337 8.71,9.29 l 3.29,3.3 9.379813,-9.4862892 c 0.946667,-0.9466662 2.362152,0.4688402 1.42,1.42 L 12.71,14.71 C 12.521281,14.897187 12.265803,15.001537 12,15 Z"
     style={{fill: "rgb(255,255,255)", fillOpacity:1, stroke: "rgb(255,255,255)", strokeWidth: 1.6}}
     />
    </g>
  )
}

export function Logomark(props) {
  return (
    <svg aria-hidden="true" viewBox="0 0 36 36" fill="none" {...props}>
      <LogomarkPaths />
    </svg>
  )
}

export function Logo(props) {
  return (
    <svg aria-hidden="true" viewBox="0 0 120 24" fill="none" {...props}>
      <LogomarkPaths />
      <text x={30} y={17} style={{fontWeight: "normal", fontFamily: "Inter, sans-serif"}}>Netchecks</text>
    </svg>
  )
}
