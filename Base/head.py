import torch
import torch.nn as nn

from Utils.utils import LOGGER

class Detect(nn.Module):
    """ Implements the head of object detection model. """
    dynamic = False     # dynamic grid-scaling, used if the input images are in different sizes
    stride = None       # strides computed during build
    export = False      # export mode: no loss or back probagate is calculated, only used for prediction
    training = True     # training mode
    def __init__(self, ch, num_class, anchors, inplace=True) -> None:
        try:
            super().__init__()
            self.num_class = num_class                       # num of detected classes
            self.num_outputs = 5 + self.num_class            # num of generated outputs (p, x, y, w, h, p1, p2, ..., pn)
            self.num_detect_layers = len(anchors)            # num of detection layers
            self.num_anchors = len(anchors[0]) // 2     # num of anchors
            self.num_layers = 1                              # num of layers

            # init grid tensors
            self.grid = [torch.empty(0) for _ in range(self.num_detect_layers)]
        
            # init anchor_grid tensors
            self.grid_anchor = [torch.empty(0) for _ in range(self.num_detect_layers)]
        
            # save weight and biases as buffer(not trainable), anchor tensor shape: [num_detect_layers, num_anchors, 2]
            self.register_buffer("anchors", torch.tensor(anchors).float().view(self.num_detect_layers, -1, 2))
        
            # save modules in module list as output conv
            self.module_list = nn.ModuleList(nn.Conv2d(x, self.num_outputs * self.num_anchors, 1) for x in ch)
        
            self.inplace = inplace
        except Exception as exp:
            LOGGER.error(f"Detect: init failed: {type(exp)}: {exp}")
            raise Exception("Detect: init failed!.")

    def forward(self, x) -> torch.Tensor:
        try:
            inference = []      # inference output
            for i in range(self.num_detect_layers):
                # pass image x to module(layer) i and create output layer x[i]
                x[i] = self.module_list[i](x[i])
            
                # get the shape of output layer: batch_size, num_channels, height and width
                batch_size, _, height, width = x[i].shape

                # change the shape of layer x to (batch_size, num_anchors, num_outputs, height, width)
                x[i] = x[i].view(batch_size, self.num_anchors, self.num_outputs, height, width).permute(0, 1, 3, 4, 2).contigous()

                # inference mode
                if not self.training:  
                    # checks if the model is using dynamic-scaling mesh grid 
                    # or the shape of the grid(height , width) is not equal to the input shape (height, width)
                    if self.dynamic or self.grid[i].shape[2:4] != x[i].shape[2:4]:
                        self.grid[i], self.grid_anchor[i] = self.make_grid(width, height, i)
                
                    # split the output into 3 tensors. conf: confidence score tensor
                    bbox_center_xy, bbox_wh, conf = x[i].sigmoid().split((2, 2, self.num_class + 1), 4)
                
                    # bbox_center_xy: center coord. of bbox tensor
                    bbox_center_xy = (bbox_center_xy * 2 + self.grid[i]) * self.stride[i]
                
                    # bbox_wh: width & height tensor
                    bbox_wh = (bbox_wh * 2) ** 2 * self.grid_anchor[i]

                    # concat bbox_center_xy, bbox_wh & confidence score
                    y = torch.cat((bbox_center_xy, bbox_wh, conf), 4)

                    # append to the output list
                    inference.append(y.view(batch_size, self.num_anchors * width * height, self.num_outputs))

            if self.training:
                return x
                    
            if self.export:
                return (torch.cat(inference, 1), )
                    
            return (torch.cat(inference, 1), x)

        except Exception as exp:
            LOGGER.error(f"Detect-forward: error: {type(exp)}, {exp}")
            raise Exception("Detect-forward: failed!")
        
    def make_grid(self, width=20, height=20, idx=0) -> any:
        """ Creates a mesh grid for center of bbox and a anchor grid for width/height of bbox. """
        try:    
            device = self.anchors[idx].device       # device of the anchor
            data_type = self.anchors[idx].dtype     # anchor data type

            # grid shape(batch_size, num_anchors, height, width, num_coord._per_anchor)
            shape = (1, self.num_anchors, height, width, 2)  

            # create 1-D tensor [0 , ... , height]
            y_coords = torch.arange(height, device=device, dtype=data_type)

            # create 1-D tensor [0, ... , width]
            x_coords = torch.arange(width, device=device, dtype=data_type)

            # create two grid cells x and y coords using given 1-D tensors
            x_cell_coords, y_cell_coords = torch.meshgrid(x_coords, y_coords, indexing='ij') 

            # create grid tensor to predict center coordinates of bbox
            # - 0.5 makes x,y coords shifts to center coords
            grid = torch.stack((x_cell_coords, y_cell_coords), 2).expand(shape) - 0.5  

            # create anchor_grid tensor to predict with and height of bbox
            anchor_grid = (self.anchors[idx] * self.stride[idx]).view((1, self.num_anchors, 1, 1, 2)).expand(shape)
            return grid, anchor_grid
        except Exception as exp:
            LOGGER.error(f"make_grid: error: {type(exp)}: {exp}")
            raise Exception("make_grid: failed!")