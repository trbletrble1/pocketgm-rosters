// visocr -- read text from an image with Apple Vision, emit JSON with per-line
// text, confidence and normalised bounding box. Boxes matter: a programme lineup
// page is a TABLE, and column position is what tells a number from a weight.
//
//   visocr <image> [--rotations]     JSON on stdout
//
// --rotations tries 0/90/180/270 and keeps whichever reads most words; dealer
// photographs of a programme are often sideways.
#import <Foundation/Foundation.h>
#import <AppKit/AppKit.h>
#import <Vision/Vision.h>
#import <ImageIO/ImageIO.h>

static NSDictionary *recognise(CGImageRef cg, CGImagePropertyOrientation orient) {
    VNRecognizeTextRequest *req = [[VNRecognizeTextRequest alloc] init];
    req.recognitionLevel = VNRequestTextRecognitionLevelAccurate;
    req.usesLanguageCorrection = NO;      // proper names and surnames, not prose
    req.recognitionLanguages = @[@"en-US"];
    if ([VNRecognizeTextRequest respondsToSelector:@selector(currentRevision)]) {
        NSIndexSet *revs = [VNRecognizeTextRequest supportedRevisions];
        if ([revs containsIndex:3]) req.revision = 3;
    }
    VNImageRequestHandler *h = [[VNImageRequestHandler alloc] initWithCGImage:cg
                                                                 orientation:orient
                                                                     options:@{}];
    NSError *err = nil;
    if (![h performRequests:@[req] error:&err]) return nil;
    NSMutableArray *lines = [NSMutableArray array];
    NSInteger words = 0;
    for (VNRecognizedTextObservation *o in req.results) {
        VNRecognizedText *t = [[o topCandidates:1] firstObject];
        if (!t) continue;
        CGRect b = o.boundingBox;
        words += [[t.string componentsSeparatedByCharactersInSet:
                   [NSCharacterSet whitespaceAndNewlineCharacterSet]]
                  filteredArrayUsingPredicate:
                  [NSPredicate predicateWithFormat:@"length > 0"]].count;
        [lines addObject:@{@"text": t.string,
                           @"conf": @(t.confidence),
                           @"x": @(b.origin.x), @"y": @(b.origin.y),
                           @"w": @(b.size.width), @"h": @(b.size.height)}];
    }
    return @{@"lines": lines, @"words": @(words)};
}

int main(int argc, const char **argv) { @autoreleasepool {
    if (argc < 2) { fprintf(stderr, "usage: visocr <image> [--rotations]\n"); return 2; }
    BOOL tryRot = NO;
    for (int i = 2; i < argc; i++) if (!strcmp(argv[i], "--rotations")) tryRot = YES;
    NSURL *u = [NSURL fileURLWithPath:[NSString stringWithUTF8String:argv[1]]];
    CGImageSourceRef src = CGImageSourceCreateWithURL((__bridge CFURLRef)u, NULL);
    if (!src) { fprintf(stderr, "cannot open image\n"); return 3; }
    CGImageRef cg = CGImageSourceCreateImageAtIndex(src, 0, NULL);
    if (!cg) { fprintf(stderr, "cannot decode image\n"); return 3; }

    CGImagePropertyOrientation orients[4] = {kCGImagePropertyOrientationUp,
                                             kCGImagePropertyOrientationRight,
                                             kCGImagePropertyOrientationDown,
                                             kCGImagePropertyOrientationLeft};
    const char *names[4] = {"up", "right", "down", "left"};
    NSDictionary *best = nil; const char *bestName = "up";
    int n = tryRot ? 4 : 1;
    for (int i = 0; i < n; i++) {
        NSDictionary *r = recognise(cg, orients[i]);
        if (!r) continue;
        if (!best || [r[@"words"] integerValue] > [best[@"words"] integerValue]) {
            best = r; bestName = names[i];
        }
    }
    if (!best) { fprintf(stderr, "vision failed\n"); return 4; }
    NSDictionary *out = @{@"image": [u path],
                          @"px_w": @(CGImageGetWidth(cg)), @"px_h": @(CGImageGetHeight(cg)),
                          @"orientation": [NSString stringWithUTF8String:bestName],
                          @"words": best[@"words"], @"lines": best[@"lines"]};
    NSData *j = [NSJSONSerialization dataWithJSONObject:out options:0 error:NULL];
    fwrite(j.bytes, 1, j.length, stdout); printf("\n");
    return 0;
} }
