#include <iostream>
#include <Eigen/Core>
#include <open3d/Open3D.h>

// helper: make a noisy sphere point cloud
open3d::geometry::PointCloud MakeSphere(int n_points, double noise = 0.02) {
    open3d::geometry::PointCloud pcd;
    std::srand(42);
    for (int i = 0; i < n_points; ++i) {
        double theta = ((double)std::rand() / RAND_MAX) * M_PI;
        double phi   = ((double)std::rand() / RAND_MAX) * 2.0 * M_PI;
        double r     = 1.0 + ((double)std::rand() / RAND_MAX - 0.5) * noise;
        pcd.points_.emplace_back(
            r * std::sin(theta) * std::cos(phi),
            r * std::sin(theta) * std::sin(phi),
            r * std::cos(theta)
        );
    }
    return pcd;
}

int main() {
    std::cout << "=== Open3D v" << OPEN3D_VERSION << " test ===\n\n";

    // ── Test 1: basic point cloud ──────────────────────────────────────────
    std::cout << "[1] Creating point cloud... ";
    auto pcd = MakeSphere(5000);
    std::cout << pcd.points_.size() << " points. OK\n";

    // ── Test 2: voxel downsampling ─────────────────────────────────────────
    std::cout << "[2] Voxel downsampling (0.1)... ";
    auto pcd_down = pcd.VoxelDownSample(0.1);
    std::cout << pcd_down->points_.size() << " points after. OK\n";

    // ── Test 3: normal estimation ──────────────────────────────────────────
    std::cout << "[3] Estimating normals... ";
    pcd_down->EstimateNormals(
        open3d::geometry::KDTreeSearchParamHybrid(0.2, 30)
    );
    std::cout << pcd_down->normals_.size() << " normals. OK\n";

    // ── Test 4: ICP ───────────────────────────────────────────────────────
    std::cout << "[4] Running ICP... ";

    // make a second cloud: same sphere, slightly rotated
    auto pcd2 = MakeSphere(5000);
    Eigen::Matrix4d small_rotation = Eigen::Matrix4d::Identity();
    double angle = 0.1; // ~5.7 degrees
    small_rotation(0,0) =  std::cos(angle);
    small_rotation(0,1) = -std::sin(angle);
    small_rotation(1,0) =  std::sin(angle);
    small_rotation(1,1) =  std::cos(angle);
    pcd2.Transform(small_rotation);

    auto pcd2_down = pcd2.VoxelDownSample(0.1);
    pcd2_down->EstimateNormals(
        open3d::geometry::KDTreeSearchParamHybrid(0.2, 30)
    );

    auto icp_result = open3d::pipelines::registration::RegistrationICP(
        *pcd_down, *pcd2_down,
        0.3,   // max correspondence distance
        Eigen::Matrix4d::Identity(),
        open3d::pipelines::registration::
            TransformationEstimationPointToPlane()
    );

    std::cout << "fitness=" << icp_result.fitness_
              << "  inlier_rmse=" << icp_result.inlier_rmse_
              << "  OK\n";

    if (icp_result.fitness_ < 0.3) {
        std::cerr << "  WARNING: ICP fitness low — check your build\n";
    }

    // ── Test 5: FPFH features ──────────────────────────────────────────────
    std::cout << "[5] Computing FPFH features... ";
    auto fpfh = open3d::pipelines::registration::ComputeFPFHFeature(
        *pcd_down,
        open3d::geometry::KDTreeSearchParamHybrid(0.5, 100)
    );
    std::cout << fpfh->data_.cols() << " feature descriptors (33-dim each). OK\n";

    // ── Test 6: pose graph types ───────────────────────────────────────────
    std::cout << "[6] Pose graph construction... ";
    open3d::pipelines::registration::PoseGraph graph;
    graph.nodes_.emplace_back(Eigen::Matrix4d::Identity());
    graph.nodes_.emplace_back(icp_result.transformation_);
    graph.edges_.emplace_back(
        open3d::pipelines::registration::PoseGraphEdge(
            0, 1,
            icp_result.transformation_,
            Eigen::Matrix6d::Identity(),
            false
        )
    );
    std::cout << graph.nodes_.size() << " nodes, "
              << graph.edges_.size() << " edges. OK\n";

    std::cout << "\nAll tests passed. Open3D is correctly installed.\n";
    return 0;
}