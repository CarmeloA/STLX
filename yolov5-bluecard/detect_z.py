import argparse
import os
import platform
import shutil
import time
from pathlib import Path

import cv2
import torch
import torch.backends.cudnn as cudnn
from numpy import random

from models.experimental import attempt_load
from utils.datasets import LoadStreams, LoadImages
from utils.general import (
    check_img_size, non_max_suppression, apply_classifier, scale_coords,
    xyxy2xywh, plot_one_box, strip_optimizer, set_logging)
from utils.torch_utils import select_device, load_classifier, time_synchronized,ModelEMA
from models.yolo import Model

f1 = open('output_txt/result.txt','w')

def detect(save_img=False):
    out, source, weights, view_img, save_txt, imgsz = \
        opt.output, opt.source, opt.weights, opt.view_img, opt.save_txt, opt.img_size
    webcam = source.isnumeric() or source.startswith('rtsp') or source.startswith('http') or source.endswith('.txt')
    # Initialize
    set_logging()
    device = select_device(opt.device)
    if os.path.exists(out):
        shutil.rmtree(out)  # delete output folder
    os.makedirs(out)  # make new output folder
    half = device.type != 'cpu'  # half precision only supported on CUDA

    # Load model
    # add by zlf at 20201027
    # load FP16 model
    # model=torch.load(weights)['model']
    # for n,p in model.named_parameters():
    #     print(p.dtype)

    # model = attempt_load(weights, map_location=device)  # load FP32 model
    # imgsz = check_img_size(imgsz, s=model.stride.max())  # check img_size


    # 20201019 load model by zlf
    # new method of loading weight;only for 'torch.save(model,state_dict())'
    net = Model('./models/yolov5s.yaml').fuse()

    # net = ModelEMA(net)
    # net = net.ema.cuda()
    state_dict = torch.load('20201110.pth', map_location=torch.device('cpu'))

    # state_dict = torch.jit.load('n.pt', map_location=torch.device('cpu'))
    # model = state_dict
    # model.cuda()

    model_dict = net.state_dict()
    for k, v in state_dict.items():
        name = k[0:]  # remove `module.`
        model_dict[name] = v
    net.load_state_dict(model_dict, strict=True)
    model = net.half().cuda()
    # model.eval()
    # input1 = torch.rand((1,3,192,320)).cuda()
    model.eval()
    # torch.jit.trace(model,input1).save('new2.pt')
    imgsz = 320
    # add by zlf at 20201009
    if half:
        model.half()  # to FP16

    # Second-stage classifier
    classify = False
    if classify:
        modelc = load_classifier(name='resnet101', n=2)  # initialize
        modelc.load_state_dict(torch.load('weights/resnet101.pt', map_location=device)['model'])  # load weights
        modelc.to(device).eval()

    # Set Dataloader
    vid_path, vid_writer = None, None
    if webcam:
        view_img = True
        cudnn.benchmark = True  # set True to speed up constant image size inference
        dataset = LoadStreams(source, img_size=imgsz)
    else:
        save_img = True
        #TODO:cudnn.benchmark = True
        dataset = LoadImages(source, img_size=imgsz)

    # Get names and colors
    # names = model.module.names if hasattr(model, 'module') else model.names
    names = ['CAR', 'CARPLATE', 'BICYCLE', 'TRICYCLE', 'PEOPLE', 'MOTORCYCLE', 'LOGO_AUDI', 'LOGO_BENZE', 'LOGO_BENZC', 'LOGO_BMW', 'LOGO_BUICK', 'LOGO_CHEVROLET', 'LOGO_CITROEN', 'LOGO_FORD', 'LOGO_HONDA', 'LOGO_HYUNDAI', 'LOGO_KIA', 'LOGO_MAZDA', 'LOGO_NISSAN', 'LOGO_PEUGEOT', 'LOGO_SKODA', 'LOGO_SUZUKI', 'LOGO_TOYOTA', 'LOGO_VOLVO', 'LOGO_VW', 'LOGO_ZHONGHUA', 'LOGO_SUBARU', 'LOGO_LEXUS', 'LOGO_CADILLAC', 'LOGO_LANDROVER', 'LOGO_JEEP', 'LOGO_BYD', 'LOGO_BYDYUAN', 'LOGO_BYDTANG', 'LOGO_CHERY', 'LOGO_CARRY', 'LOGO_HAVAL', 'LOGO_GREATWALL', 'LOGO_GREATWALLOLD', 'LOGO_ROEWE', 'LOGO_JAC', 'LOGO_HAFEI', 'LOGO_SGMW', 'LOGO_CASY', 'LOGO_CHANAJNX', 'LOGO_CHANGAN', 'LOGO_CHANA', 'LOGO_CHANGANCS', 'LOGO_XIALI', 'LOGO_FAW', 'LOGO_YQBT', 'LOGO_REDFLAG', 'LOGO_GEELY', 'LOGO_EMGRAND', 'LOGO_GLEAGLE', 'LOGO_ENGLON', 'LOGO_BAOJUN', 'LOGO_DF', 'LOGO_JINBEI', 'LOGO_BAIC', 'LOGO_WEIWANG', 'LOGO_HUANSU', 'LOGO_FOTON', 'LOGO_HAIMA', 'LOGO_ZOTYEAUTO', 'LOGO_MITSUBISHI', 'LOGO_RENAULT', 'LOGO_MG', 'LOGO_DODGE', 'LOGO_FIAT', 'LOGO_INFINITI', 'LOGO_MINI', 'LOGO_TESLA', 'LOGO_SMART', 'LOGO_BORGWARD', 'LOGO_JAGUAR', 'LOGO_HUMMER', 'LOGO_PORSCHE', 'LOGO_LAMBORGHINI', 'LOGO_DS', 'LOGO_CROWN', 'LOGO_LUXGEN', 'LOGO_ACURA', 'LOGO_LINCOLN', 'LOGO_SOUEAST', 'LOGO_VENUCIA', 'LOGO_TRUMPCHI', 'LOGO_LEOPAARD', 'LOGO_ZXAUTO', 'LOGO_LIFAN', 'LOGO_HUANGHAI', 'LOGO_HAWTAI', 'LOGO_REIZ', 'LOGO_CHANGHE', 'LOGO_GOLDENDRAGON', 'LOGO_YUTONG', 'LOGO_HUIZHONG', 'LOGO_JMC', 'LOGO_JMCYUSHENG', 'LOGO_LANDWIND', 'LOGO_NAVECO', 'LOGO_QOROS', 'LOGO_OPEL', 'LOGO_YUEJING']

    colors = [[random.randint(0, 255) for _ in range(3)] for _ in range(len(names))]

    # Run inference
    t0 = time.time()
    img = torch.zeros((1, 3, imgsz, imgsz), device=device)  # init img
    # _ = model(img.half() if half else img) if device.type != 'cpu' else None  # run once
    for path, img, im0s, vid_cap in dataset:
        f1.write('%s:'%(path.split('/')[-1]))
        img = torch.from_numpy(img).to(device)
        img = img.half() if half else img.float()  # uint8 to fp16/32
        img /= 255.0  # 0 - 255 to 0.0 - 1.0
        if img.ndimension() == 3:
            img = img.unsqueeze(0)

        # Inference
        t1 = time_synchronized()

        pred = model(img, augment=opt.augment)[0]
        # pred = model(img.cuda())
        # pred = list(pred)
        # pred = detectz(pred)




        # Apply NMS
        pred = non_max_suppression(pred, opt.conf_thres, opt.iou_thres, classes=opt.classes, agnostic=opt.agnostic_nms)
        t2 = time_synchronized()

        # Apply Classifier
        if classify:
            pred = apply_classifier(pred, modelc, img, im0s)

        # Process detections
        for i, det in enumerate(pred):  # detections per image
            if webcam:  # batch_size >= 1
                p, s, im0 = path[i], '%g: ' % i, im0s[i].copy()
            else:
                p, s, im0 = path, '', im0s

            save_path = str(Path(out) / Path(p).name)
            txt_path = str(Path(out) / Path(p).stem) + ('_%g' % dataset.frame if dataset.mode == 'video' else '')
            s += '%gx%g ' % img.shape[2:]  # print string
            gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
            if det is not None and len(det):
                # Rescale boxes from img_size to im0 size
                det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()

                # Print results
                for c in det[:, -1].unique():
                    n = (det[:, -1] == c).sum()  # detections per class
                    s += '%g %ss, ' % (n, names[int(c)])  # add to string

                # Write results
                for *xyxy, conf, cls, obj_conf, cls_conf in reversed(det): # add by zlf at 20201026
                    # add by zlf at 20201019
                    x1 = int(xyxy[0].item())
                    y1 = int(xyxy[1].item())
                    x2 = int(xyxy[2].item())
                    y2 = int(xyxy[3].item())
                    f1.write("[%s,%.2f,%d,%d,%d,%d]" % (
                    names[int(cls.item())], round((conf.item() * 100),2), x1, y1, x2, y2))
                    # add by zlf at 20201019

                    if save_txt:  # Write to file
                        xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # normalized xywh
                        with open(txt_path + '.txt', 'a') as f:
                            f.write(('%g ' * 5 + '\n') % (cls, *xywh))  # label format

                    if save_img or view_img:  # Add bbox to image
                        label = '%s|%.2f|%.2f|%.2f' % (names[int(cls)], conf,obj_conf,cls_conf)
                        plot_one_box(xyxy, im0, label=label, color=colors[int(cls)], line_thickness=3)
            f1.write('\n')
            # Print time (inference + NMS)
            print('%sDone. (%.3fs)' % (s, t2 - t1))

            # Stream results
            if view_img:
                cv2.imshow(p, im0)
                if cv2.waitKey(1) == ord('q'):  # q to quit
                    raise StopIteration

            # Save results (image with detections)
            if save_img:
                if dataset.mode == 'images':
                    cv2.imwrite(save_path, im0)
                else:
                    if vid_path != save_path:  # new video
                        vid_path = save_path
                        if isinstance(vid_writer, cv2.VideoWriter):
                            vid_writer.release()  # release previous video writer

                        fourcc = 'mp4v'  # output video codec
                        fps = vid_cap.get(cv2.CAP_PROP_FPS)
                        w = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        h = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        vid_writer = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*fourcc), fps, (w, h))
                    vid_writer.write(im0)

    if save_txt or save_img:
        print('Results saved to %s' % Path(out))
        if platform.system() == 'Darwin' and not opt.update:  # MacOS
            os.system('open ' + save_path)

    print('Done. (%.3fs)' % (time.time() - t0))

# 20201109
def detectz(x):
    nc = 104
    no = 109
    anchors = [[10, 13, 16, 30, 33, 23], [30, 61, 62, 45, 59, 119], [116, 90, 156, 198, 373, 326]]
    nl = len(anchors)
    na = len(anchors[0])//2
    grid = [torch.zeros(1)] * nl
    a = torch.tensor(anchors).float().view(nl, -1, 2).cuda()
    anchor_grid = a.clone().view(nl, 1, -1, 1, 1, 2)
    stride = torch.tensor([8.,16.,32.]).cuda()
    # ch = [327,327,327]
    # m = nn.ModuleList(nn.Conv2d(x, no * na, 1) for x in ch)
    z = []  # inference output

    for i in range(nl):
        # x[i] = m[i](x[i])
        bs, _, ny, nx = x[i].shape  # x(bs,255,20,20) to x(bs,3,20,20,85)
        x[i] = x[i].view(bs, 3, 109, ny, nx).permute(0, 1, 3, 4, 2).contiguous()
        if grid[i].shape[2:4] != x[i].shape[2:4]:
            grid[i] = make_grid(nx, ny).to(x[i].device)
        y = x[i].sigmoid()
        y[..., 0:2] = (y[..., 0:2] * 2. - 0.5 + grid[i].to(x[i].device)) * stride[i]  # xy
        y[..., 2:4] = (y[..., 2:4] * 2) ** 2 * anchor_grid[i]  # wh
        z.append(y.view(bs, -1, no))

    return torch.cat(z, 1)


def make_grid(nx=20, ny=20):
    yv, xv = torch.meshgrid([torch.arange(ny), torch.arange(nx)])
    return torch.stack((xv, yv), 2).view((1, 1, ny, nx, 2)).float()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', nargs='+', type=str, default='/home/data/yolov5_pt/runs/exp7/weights/ckpt_model_350_800_0.09017.pt', help='model.pt path(s)')
    parser.add_argument('--source', type=str, default='/home/sysman/zlf/ng', help='source')  # file/folder, 0 for webcam
    parser.add_argument('--output', type=str, default='inference/20201110', help='output folder')  # output folder
    parser.add_argument('--img-size', type=int, default=320, help='inference size (pixels)')
    parser.add_argument('--conf-thres', type=float, default=0.3, help='object confidence threshold')
    parser.add_argument('--iou-thres', type=float, default=0.3, help='IOU threshold for NMS')
    parser.add_argument('--device', default='1', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
    parser.add_argument('--view-img', action='store_true', help='display results')
    parser.add_argument('--save-txt', action='store_true', help='save results to *.txt')
    parser.add_argument('--classes', nargs='+', type=int, help='filter by class: --class 0, or --class 0 2 3')
    parser.add_argument('--agnostic-nms', action='store_true', help='class-agnostic NMS')
    parser.add_argument('--augment', action='store_true', help='augmented inference')
    parser.add_argument('--update', action='store_true', help='update all models')
    opt = parser.parse_args()
    print(opt)



    with torch.no_grad():
        if opt.update:  # update all models (to fix SourceChangeWarning)
            for opt.weights in ['yolov5s.pt', 'yolov5m.pt', 'yolov5l.pt', 'yolov5x.pt']:
                detect()
                strip_optimizer(opt.weights)
        else:
            detect()
