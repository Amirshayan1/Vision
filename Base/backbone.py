import torch
import torch.nn as nn
import torch.nn.functional as F

class ConvLayer(nn.Module):
    # class ConvLayer constructs a conv layer, BatchNorm and SiLU constructed with args:
    # [layer_name, input_channel, output_channel, kernel, stride, padding, groups, dilation]
    def __init__(self, c_in, c_out, k=1, s=1, p=None, g=1, d=1, activation=True):
        super().__init__()
        self.conv = nn.Conv2d(c_in, c_out, k, s, p, groups=g, dilation=d, bias=False)
        self.bn = nn.BatchNorm2d(c_out)
        self.activation = nn.SiLU() if activation is True else nn.Identity()
    
    def forward(self, x):
        # apply CBS block input and return the output
        return self.activation(self.bn(self.conv(x)))

class Bottleneck(nn.Module):
    # class Bottleneck implements the block to reduce the number of channels in feature map using args:
    # [input_channel, output_channel, groups, c_hidden_ratio]
    def __init__(self, c_in, c_out, g=1, e=0.5):
        super().__init__()
        c_hidden = int(e * c_out)
        self.conv1 = ConvLayer(c_in, c_hidden, 1, 1)
        self.conv2 = ConvLayer(c_hidden, c_out, 3 ,1, g=g)

    def forward(self, x):
        return self.conv2(self.conv1(x))


class C3Layer(nn.Module):
    # class C3Layer implements block CSP Bottleneck block in backbone containing 3 ConvLayer and Bottleneck using args:
    # [input_channel, output_channel, num_bottleneck_layers groups, c_hidden_ratio]
    def __init__(self, c_in, c_out, n=1, g=1, e=0.5):
        super().__init__()
        c_hidden = int(e * c_in)
        self.conv1 = ConvLayer(c_in, c_hidden, 1, 1)
        self.conv2 = ConvLayer(c_in, c_hidden, 1, 1)
        self.conv3 = ConvLayer(2* c_hidden, c_out, 1, 1)
        self.bottleneck = nn.Sequential(*(Bottleneck(c_hidden, c_hidden, 1, e=1) for _ in range(n)))

    def forward(self, x):
        return self.conv3(torch.cat((self.bottleneck(self.conv1(x)), self.conv2(x)), 1))
        
class SPPF(nn.Module):
    # implements Spatial Pyramid Pooling - Fast using followig args:
    # [input_channel, output_channel, hiiden_ratio, kernel_size]
    def __init__(self, c_in, c_out, e=2, k=5):
        super().__init__()
        c_hidden = c_in // e    # hidden channel size
        self.conv1 = ConvLayer(c_in, c_hidden, 1, 1)
        self.conv2 = ConvLayer(c_hidden *4 , c_out, 1, 1)
        self.maxPool = nn.MaxPool2d(kernel_size=k, stride=1, padding=k//e)

    def forward(self, x):
        x = self.conv1(x)
        max1 = self.maxPool(x)
        max2 = self.maxPool(max1)
        return self.conv2(torch.cat((x, max1, max2, self.maxPool(max2)), 1))