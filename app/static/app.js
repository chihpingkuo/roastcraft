async function App() {
  const width = 640;
  const height = 400;
  const marginTop = 20;
  const marginRight = 20;
  const marginBottom = 30;
  const marginLeft = 40;

  let store = Alpine.reactive({ data: [] });

  // Declare the x (horizontal position) scale.
  const x = d3
    .scaleLinear()
    .domain([0, 900])
    .range([marginLeft, width - marginRight]);

  // Declare the y (vertical position) scale.
  const y = d3
    .scaleLinear()
    .domain([0, 100])
    .range([height - marginBottom, marginTop]);

  // Declare the line generator.
  const line = d3
    .line()
    .x((d) => x(d.t))
    .y((d) => y(d.v));

  // Create the SVG container.
  const svg = d3.create("svg").attr("width", width).attr("height", height);

  // Add the x-axis.
  svg
    .append("g")
    .attr("transform", `translate(0,${height - marginBottom})`)
    .call(d3.axisBottom(x));

  // Add the y-axis.
  svg
    .append("g")
    .attr("transform", `translate(${marginLeft},0)`)
    .call(d3.axisLeft(y));

  // Append a path for the line.
  svg
    .append("path")
    .attr("id", "id1")
    .attr("fill", "none")
    .attr("stroke", "steelblue")
    .attr("stroke-width", 1.5)
    .attr("d", line(store.data));

  Alpine.effect(() => {
    d3.select("#id1").attr("d", line(store.data));
  });

  // Append the SVG element.
  const container = document.getElementById("container");
  container.append(svg.node());

  // const socket = io("http://localhost:8000", {
  //   opts: { path: "/socket.io" },
  // });
  const socket = io();

  console.log(socket);
  socket.on("tick", (msg) => {
    console.log(msg);
    store.data = msg;
  });
}

export default App;
