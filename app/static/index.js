import { createApp, ref, onMounted, reactive, watchEffect  } from 'vue'

const app = createApp({
    setup() {
        
        const message = ref('Hello Vue!')
        
        const main_chart = ref()

        let store = reactive({
            channels: settings.channels.map((c) => ({
              id: c.id,
              color: c.color,
              data: [],
              ror: [],
              ror_filtered: [],
              ror_smoothed: []
            })),
            
            roast_events: {}
          });

        let channels_nodes = [];    

        onMounted(() => {    
        
            const width = 860;
            const height = 550;
            const marginTop = 20;
            const marginRight = 20;
            const marginBottom = 30;
            const marginLeft = 40;
            
            // Declare the x (horizontal position) scale.
            const xScale = d3
            .scaleLinear()
            .domain([-60, 780])
            .range([marginLeft, width - marginRight]);

            // Declare the y (vertical position) scale.
            const yScale = d3
            .scaleLinear()
            .domain([80, 380])
            .range([height - marginBottom, marginTop]);

            // Declare the y (vertical position) scale.
            const yScaleROR = d3
            .scaleLinear()
            .domain([0, 24])
            .range([height - marginBottom, marginTop]);

            // Declare the line generator.
            const line = d3.line()
            .x((p) => xScale(p.t))
            .y((p) => yScale(p.v));

            const lineROR = d3.line()
            .x((p) => xScale(p.t))
            .y((p) => yScaleROR(p.v));

            // Create the SVG container.
            const svg = d3.select("#main_chart")
                .attr("width", width)
                .attr("height", height);
            
            // Add the x-axis.
            svg
                .append("g")
                .attr("transform", `translate(0,${height - marginBottom})`)
                .call(d3.axisBottom(xScale));

            // Add the y-axis.
            svg
                .append("g")
                .attr("transform", `translate(${marginLeft},0)`)
                .call(d3.axisLeft(yScale));

            svg
                .append("g")
                .attr("transform", `translate(${width - marginRight},0)`)
                .call(d3.axisRight(yScaleROR));      

            store.channels.forEach((channel) => {
                channels_nodes.push(
                    svg
                    .append("path")
                    // .attr("id", channel.id)
                    .attr("fill", "none")
                    .attr("stroke", channel.color)
                    .attr("stroke-width", 1.5)
                    .attr("d", line(channel.data))
                )
            });
        
            let roast_events_node = svg.append("g")
            
            watchEffect(() => {
                for(let i = 0 ; i < store.channels.length ; i++) {
                  channels_nodes[i].attr("d", line(store.channels[i].data));  
                }
            
               
            });
            
        })

        // const socket = io("http://localhost:8000", {
        //   opts: { path: "/socket.io" },
        // });
        const socket = io();

        socket.on("read_device", (channels) => {
            console.log(channels);
            store.channels = channels;
        });

        return {
            message
        }
    }
})

// Delimiters changed to ES6 template string style
app.config.compilerOptions.delimiters = ['${', '}']

app.mount('#app')
